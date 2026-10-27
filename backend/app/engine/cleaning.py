"""Cleaning operations.

Each operation is a small class registered in `OPERATIONS`. Operations never
modify their input frame; they return a new frame plus a description of what
changed, so callers can preview a change before saving it. The dataset store
keeps the original upload, so every operation can be undone by resetting.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from app.engine.profiling import (
    DATE_FORMATS,
    NUMERIC,
    best_date_format,
    infer_column,
    parse_dates,
    parse_numeric,
)


class CleaningError(ValueError):
    """Raised when an operation cannot be applied with the given parameters."""


@dataclass
class ParamSpec:
    name: str
    label: str
    kind: str  # "column", "choice" or "text"
    required: bool = True
    choices: list[str] = field(default_factory=list)
    default: str | None = None
    help: str = ""


@dataclass
class OperationResult:
    operation: str
    params: dict
    rows_before: int
    rows_after: int
    columns_before: int
    columns_after: int
    cells_changed: int
    summary: str
    warnings: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.cells_changed > 0 or self.rows_before != self.rows_after or self.columns_before != self.columns_after

    def to_dict(self) -> dict:
        data = asdict(self)
        data["rows_removed"] = self.rows_before - self.rows_after
        data["changed"] = self.changed
        return data


def _require_column(frame: pd.DataFrame, params: dict) -> str:
    column = params.get("column")
    if not column:
        raise CleaningError("Choose a column for this operation.")
    if column not in frame.columns:
        raise CleaningError(f"Column '{column}' does not exist in this dataset.")
    return column


def _changed_cells(before: pd.Series, after: pd.Series) -> int:
    before_text = before.astype("string")
    after_text = after.astype("string")
    both_missing = before_text.isna() & after_text.isna()
    differs = before_text.fillna("\0") != after_text.fillna("\0")
    return int((differs & ~both_missing).sum())


class Operation:
    key: str = ""
    label: str = ""
    description: str = ""
    consequence: str = ""
    params: list[ParamSpec] = []

    def apply(self, frame: pd.DataFrame, params: dict) -> tuple[pd.DataFrame, OperationResult]:
        raise NotImplementedError

    def describe(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "consequence": self.consequence,
            "params": [asdict(param) for param in self.params],
        }

    def _result(
        self, params: dict, before: pd.DataFrame, after: pd.DataFrame, cells: int, summary: str, warnings=None
    ) -> OperationResult:
        return OperationResult(
            operation=self.key,
            params=params,
            rows_before=len(before),
            rows_after=len(after),
            columns_before=before.shape[1],
            columns_after=after.shape[1],
            cells_changed=cells,
            summary=summary,
            warnings=warnings or [],
        )


class RemoveDuplicates(Operation):
    key = "remove_duplicates"
    label = "Remove duplicate rows"
    description = "Deletes rows that are exact copies of an earlier row, keeping the first occurrence."
    consequence = "Removed rows are no longer counted in totals. Rows that differ in any column are kept."
    params = []

    def apply(self, frame, params):
        result = frame.drop_duplicates(keep="first").reset_index(drop=True)
        removed = len(frame) - len(result)
        return result, self._result(params, frame, result, 0, f"Removed {removed:,} duplicate rows.")


class FillMissing(Operation):
    key = "fill_missing"
    label = "Fill missing values"
    description = "Replaces empty cells in one column with a fixed value or a statistic of that column."
    consequence = "Filled values are estimates, not observations. Mean and median fills can make the column look less varied than it really is."
    params = [
        ParamSpec("column", "Column", "column"),
        ParamSpec("strategy", "Fill with", "choice", choices=["constant", "mean", "median", "mode"], default="constant"),
        ParamSpec("value", "Value", "text", required=False, help="Used when 'Fill with' is constant."),
    ]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        strategy = params.get("strategy") or "constant"
        series = frame[column]
        missing = int(series.isna().sum())
        profile = infer_column(series)
        if strategy == "constant":
            value = params.get("value")
            if value is None or str(value).strip() == "":
                raise CleaningError("Enter the value to use for empty cells.")
            fill_value = str(value)
            if profile.inferred_type == NUMERIC and pd.isna(parse_numeric(pd.Series([fill_value])).iloc[0]):
                raise CleaningError(f"'{column}' is numeric, so the fill value must be a number.")
        elif strategy in ("mean", "median"):
            if profile.inferred_type != NUMERIC:
                raise CleaningError(
                    f"{strategy.title()} can only be used on numeric columns; '{column}' is {profile.inferred_type}."
                )
            numbers = parse_numeric(series)
            if numbers.dropna().empty:
                raise CleaningError(f"'{column}' has no numeric values to calculate a {strategy} from.")
            statistic = numbers.mean() if strategy == "mean" else numbers.median()
            fill_value = f"{round(float(statistic), 4):g}"
        elif strategy == "mode":
            modes = series.dropna().mode()
            if modes.empty:
                raise CleaningError(f"'{column}' has no values to take the most common value from.")
            fill_value = str(modes.iloc[0])
        else:
            raise CleaningError(f"Unknown fill strategy '{strategy}'.")
        result = frame.copy()
        result[column] = series.astype("object").where(series.notna(), fill_value).astype("str")
        return result, self._result(
            params, frame, result, missing, f"Filled {missing:,} empty cells in '{column}' with {fill_value!r}."
        )


class DropMissingRows(Operation):
    key = "drop_missing_rows"
    label = "Remove rows with missing values"
    description = "Deletes every row where the chosen column is empty."
    consequence = "Removed rows are excluded from all analysis, including columns that did have values."
    params = [ParamSpec("column", "Column", "column")]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        result = frame[frame[column].notna()].reset_index(drop=True)
        removed = len(frame) - len(result)
        return result, self._result(params, frame, result, 0, f"Removed {removed:,} rows with no value in '{column}'.")


class ConvertNumeric(Operation):
    key = "convert_numeric"
    label = "Convert to numbers"
    description = "Rewrites a column as plain numbers, removing currency symbols and thousands separators."
    consequence = (
        "Values that cannot be read as numbers become empty. Use 'Remove invalid rows' instead if those rows should be excluded."
    )
    params = [ParamSpec("column", "Column", "column")]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        before = frame[column]
        numbers = parse_numeric(before)
        invalid = int((before.notna() & numbers.isna()).sum())
        formatted = numbers.map(lambda value: None if pd.isna(value) else f"{value:.10g}")
        result = frame.copy()
        result[column] = formatted.astype("str")
        result.loc[numbers.isna(), column] = None
        cells = _changed_cells(before, result[column])
        warnings = [f"{invalid:,} values could not be read as numbers and are now empty."] if invalid else []
        return result, self._result(
            params, frame, result, cells, f"Converted '{column}' to numbers; {cells:,} cells changed.", warnings
        )


class ConvertDatetime(Operation):
    key = "convert_datetime"
    label = "Convert to dates"
    description = "Rewrites a column as ISO dates (YYYY-MM-DD) using one consistent date format."
    consequence = "Values that do not match the format become empty and are excluded from time-based analysis."
    params = [
        ParamSpec("column", "Column", "column"),
        ParamSpec(
            "format",
            "Date format",
            "choice",
            required=False,
            choices=["auto", *DATE_FORMATS],
            default="auto",
            help="'auto' picks the format that reads the most values.",
        ),
    ]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        before = frame[column]
        date_format = params.get("format") or "auto"
        if date_format == "auto":
            date_format, rate = best_date_format(before.dropna())
            if not date_format or rate < 0.5:
                raise CleaningError(f"'{column}' does not look like a date column; fewer than half of its values are dates.")
        elif date_format not in DATE_FORMATS:
            raise CleaningError(f"Unsupported date format '{date_format}'.")
        dates = parse_dates(before, date_format)
        has_time = bool((dates.dropna() != dates.dropna().dt.normalize()).any())
        output_format = "%Y-%m-%d %H:%M:%S" if has_time else "%Y-%m-%d"
        result = frame.copy()
        result[column] = dates.dt.strftime(output_format).astype("str")
        result.loc[dates.isna(), column] = None
        invalid = int((before.notna() & dates.isna()).sum())
        cells = _changed_cells(before, result[column])
        warnings = [f"{invalid:,} values did not match {date_format} and are now empty."] if invalid else []
        return result, self._result(
            params, frame, result, cells, f"Converted '{column}' to dates using {date_format}; {cells:,} cells changed.", warnings
        )


class NormaliseText(Operation):
    key = "normalise_text"
    label = "Normalise text"
    description = "Trims surrounding spaces, collapses repeated spaces and optionally applies consistent capitalisation."
    consequence = "Values that differed only in spacing or capitalisation become identical and are grouped together."
    params = [
        ParamSpec("column", "Column", "column"),
        ParamSpec(
            "case", "Capitalisation", "choice", required=False, choices=["keep", "title", "lower", "upper"], default="title"
        ),
    ]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        case = params.get("case") or "keep"
        if case not in {"keep", "title", "lower", "upper"}:
            raise CleaningError(f"Unknown capitalisation option '{case}'.")
        before = frame[column]
        text = before.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        if case == "title":
            text = text.str.title()
        elif case == "lower":
            text = text.str.lower()
        elif case == "upper":
            text = text.str.upper()
        result = frame.copy()
        result[column] = text.astype("str")
        result.loc[before.isna(), column] = None
        cells = _changed_cells(before, result[column])
        return result, self._result(params, frame, result, cells, f"Normalised text in '{column}'; {cells:,} cells changed.")


class RemoveInvalidRows(Operation):
    key = "remove_invalid_rows"
    label = "Remove invalid rows"
    description = "Deletes rows where the chosen column has a value that cannot be read as a number or date."
    consequence = "Removed rows are excluded from all analysis. Empty cells are not affected."
    params = [
        ParamSpec("column", "Column", "column"),
        ParamSpec("kind", "Expected type", "choice", choices=["number", "date"], default="number"),
    ]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        kind = params.get("kind") or "number"
        values = frame[column]
        if kind == "number":
            parsed = parse_numeric(values)
        elif kind == "date":
            date_format, _ = best_date_format(values.dropna())
            parsed = parse_dates(values, date_format)
        else:
            raise CleaningError("Expected type must be 'number' or 'date'.")
        invalid = values.notna() & parsed.isna()
        result = frame[~invalid].reset_index(drop=True)
        return result, self._result(
            params, frame, result, 0, f"Removed {int(invalid.sum()):,} rows with an invalid {kind} in '{column}'."
        )


class DropColumn(Operation):
    key = "drop_column"
    label = "Remove column"
    description = "Removes one column from the working copy of the dataset."
    consequence = "The column is no longer available for analysis or reports. Reset the dataset to restore it."
    params = [ParamSpec("column", "Column", "column")]

    def apply(self, frame, params):
        column = _require_column(frame, params)
        if frame.shape[1] == 1:
            raise CleaningError("A dataset must keep at least one column.")
        result = frame.drop(columns=[column])
        return result, self._result(params, frame, result, 0, f"Removed column '{column}'.")


OPERATIONS: dict[str, Operation] = {
    operation.key: operation
    for operation in (
        RemoveDuplicates(),
        FillMissing(),
        DropMissingRows(),
        ConvertNumeric(),
        ConvertDatetime(),
        NormaliseText(),
        RemoveInvalidRows(),
        DropColumn(),
    )
}


def apply_operation(frame: pd.DataFrame, key: str, params: dict | None = None) -> tuple[pd.DataFrame, OperationResult]:
    operation = OPERATIONS.get(key)
    if operation is None:
        raise CleaningError(f"Unknown cleaning operation '{key}'.")
    clean_params = {name: value for name, value in (params or {}).items() if value is not None}
    return operation.apply(frame, clean_params)
