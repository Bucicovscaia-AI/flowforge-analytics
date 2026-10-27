"""Column type inference and business role detection.

All values arrive as strings (see `loading.py`). Each column is assigned one
semantic type based on how many of its non-missing values can be read as that
type. A column where at least `TYPE_THRESHOLD` of values parse as numbers or
dates is treated as numeric or date; the remaining unparseable values are
counted as invalid so the data quality engine can report them, and analysis
excludes them rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

import pandas as pd

TYPE_THRESHOLD = 0.9

NUMERIC = "numeric"
DATETIME = "datetime"
BOOLEAN = "boolean"
CATEGORICAL = "categorical"
TEXT = "text"
IDENTIFIER = "identifier"
EMPTY = "empty"

# Day-first formats are tried before month-first ones, so ambiguous dates such as
# 03/04/2025 are read as 3 April. The chosen format is reported in the profile.
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M",
    "%d %b %Y",
    "%b %d %Y",
    "%Y-%m",
]

_BOOLEAN_TOKENS = {"true", "false", "yes", "no", "y", "n"}
_CURRENCY_CHARS = re.compile(r"[£$€¥\s]")
_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_LEADING_ZERO = re.compile(r"^0\d+$")
_DATE_SHAPE = re.compile(r"\d{1,4}[-/. ]\w{1,9}(?:[-/. ]\d{1,4})?")


def parse_numeric(values: pd.Series) -> pd.Series:
    """Convert strings to floats, accepting currency symbols and thousands separators.

    Values that cannot be read become NaN.
    """
    text = values.astype("string").str.replace(_CURRENCY_CHARS, "", regex=True)
    with_thousands = text.str.match(_THOUSANDS).fillna(False)
    text = text.where(~with_thousands, text.str.replace(",", "", regex=False))
    return pd.to_numeric(text, errors="coerce").astype("float64")


def parse_dates(values: pd.Series, date_format: str | None) -> pd.Series:
    text = values.astype("string").str.strip()
    if date_format:
        return pd.to_datetime(text, format=date_format, errors="coerce")
    return pd.to_datetime(text, format="mixed", errors="coerce", dayfirst=True)


def best_date_format(values: pd.Series) -> tuple[str | None, float]:
    """Return the date format that parses the largest share of values, and that share."""
    non_null = values.dropna()
    if non_null.empty:
        return None, 0.0
    sample = non_null.head(2000)
    if not sample.astype("string").str.contains(_DATE_SHAPE, regex=True).fillna(False).mean() >= 0.5:
        return None, 0.0
    best_format, best_rate = None, 0.0
    for date_format in DATE_FORMATS:
        rate = float(parse_dates(sample, date_format).notna().mean())
        if rate > best_rate:
            best_format, best_rate = date_format, rate
        if rate == 1.0:
            break
    return best_format, best_rate


def normalise_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _name_tokens(name: str) -> set[str]:
    normalised = normalise_name(name)
    tokens = set(normalised.split("_"))
    tokens.add(normalised)
    # Split camelCase names such as orderDate.
    for part in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", name):
        tokens.add(part.lower())
    return tokens


@dataclass
class ColumnProfile:
    name: str
    inferred_type: str
    non_null_count: int
    missing_count: int
    missing_percent: float
    distinct_count: int
    invalid_count: int = 0
    date_format: str | None = None
    sample_values: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DatasetProfile:
    row_count: int
    column_count: int
    columns: list[ColumnProfile]

    def column(self, name: str) -> ColumnProfile | None:
        return next((column for column in self.columns if column.name == name), None)

    def names_of_type(self, *types: str) -> list[str]:
        return [column.name for column in self.columns if column.inferred_type in types]

    def to_dict(self) -> dict:
        return {
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [column.to_dict() for column in self.columns],
        }


def infer_column(series: pd.Series) -> ColumnProfile:
    name = str(series.name)
    total = len(series)
    non_null = series.dropna()
    missing = total - len(non_null)
    distinct = int(non_null.nunique())
    samples = [str(value) for value in non_null.drop_duplicates().head(5)]
    base = dict(
        name=name,
        non_null_count=len(non_null),
        missing_count=int(missing),
        missing_percent=round(missing / total * 100, 2) if total else 0.0,
        distinct_count=distinct,
        sample_values=samples,
    )
    if non_null.empty:
        return ColumnProfile(inferred_type=EMPTY, **base)

    stripped = non_null.astype("string").str.strip()
    has_leading_zeros = bool(stripped.str.match(_LEADING_ZERO).fillna(False).any())
    tokens = _name_tokens(name)
    looks_like_id = bool(tokens & {"id", "uuid", "code", "ref", "reference", "sku", "number", "no"}) or normalise_name(
        name
    ).endswith("id")

    if not has_leading_zeros:
        numeric = parse_numeric(stripped)
        numeric_rate = float(numeric.notna().mean())
        if numeric_rate >= TYPE_THRESHOLD:
            invalid = int(numeric.isna().sum())
            unique_integers = distinct == len(non_null) and bool((numeric.dropna() % 1 == 0).all())
            inferred = IDENTIFIER if (looks_like_id and unique_integers) else NUMERIC
            return ColumnProfile(inferred_type=inferred, invalid_count=invalid, **base)

    lowered = set(stripped.str.lower().unique())
    if lowered and lowered <= _BOOLEAN_TOKENS and len(lowered) <= 2:
        return ColumnProfile(inferred_type=BOOLEAN, **base)

    date_format, date_rate = best_date_format(stripped)
    if date_format and date_rate >= TYPE_THRESHOLD:
        invalid = int(parse_dates(stripped, date_format).isna().sum())
        return ColumnProfile(inferred_type=DATETIME, invalid_count=invalid, date_format=date_format, **base)

    unique_ratio = distinct / len(non_null)
    if looks_like_id and unique_ratio >= 0.95:
        inferred = IDENTIFIER
    elif distinct <= 50 or (unique_ratio <= 0.2 and distinct <= 1000):
        inferred = CATEGORICAL
    elif (
        unique_ratio >= 0.98
        and len(non_null) >= 20
        and not stripped.str.contains(r"\s", regex=True).any()
        and stripped.str.len().max() <= 40
    ):
        inferred = IDENTIFIER
    else:
        inferred = TEXT
    return ColumnProfile(inferred_type=inferred, **base)


def profile_frame(frame: pd.DataFrame) -> DatasetProfile:
    columns = [infer_column(frame[name]) for name in frame.columns]
    return DatasetProfile(row_count=len(frame), column_count=frame.shape[1], columns=columns)


def typed_frame(frame: pd.DataFrame, profile: DatasetProfile) -> pd.DataFrame:
    """Return a copy with numeric and date columns converted; invalid values become missing."""
    typed = frame.copy()
    for column in profile.columns:
        if column.inferred_type in (NUMERIC, IDENTIFIER) and column.name in typed:
            converted = parse_numeric(typed[column.name])
            if column.inferred_type == NUMERIC or converted.notna().mean() >= TYPE_THRESHOLD:
                typed[column.name] = converted
        elif column.inferred_type == DATETIME:
            typed[column.name] = parse_dates(typed[column.name], column.date_format)
        elif column.inferred_type == BOOLEAN:
            lowered = typed[column.name].astype("string").str.strip().str.lower()
            typed[column.name] = lowered.map(lambda value: None if pd.isna(value) else value in {"true", "yes", "y"}).astype(
                "boolean"
            )
    return typed


# ---------------------------------------------------------------------------
# Business roles
# ---------------------------------------------------------------------------

ROLE_DEFINITIONS: dict[str, dict] = {
    "date": {
        "label": "Date",
        "types": (DATETIME,),
        "keywords": [["order_date", "date"], ["timestamp", "time", "day", "created", "period", "month"]],
    },
    "quantity": {
        "label": "Quantity",
        "types": (NUMERIC,),
        "keywords": [["quantity", "qty"], ["units", "volume", "items", "count"]],
    },
    "unit_price": {
        "label": "Unit price",
        "types": (NUMERIC,),
        "keywords": [["unit_price", "unitprice", "price"], ["unit_cost", "rate"]],
    },
    "revenue": {
        "label": "Revenue",
        "types": (NUMERIC,),
        "keywords": [["revenue"], ["sales", "sale"], ["amount"], ["total", "turnover", "income", "gross", "value"]],
    },
    "category": {
        "label": "Category",
        "types": (CATEGORICAL, TEXT),
        "keywords": [["category", "categories"], ["segment", "department", "type", "group", "class", "family"]],
    },
    "product": {
        "label": "Product",
        "types": (CATEGORICAL, TEXT),
        "keywords": [["product", "product_name"], ["item", "model", "article", "service", "description"]],
    },
    "region": {
        "label": "Region",
        "types": (CATEGORICAL, TEXT),
        "keywords": [
            ["region"],
            ["country", "state", "city", "territory", "market", "area", "location", "store", "branch", "zone"],
        ],
    },
    "status": {
        "label": "Status",
        "types": (CATEGORICAL,),
        "keywords": [["status", "order_status"], ["state", "stage"]],
    },
}

ROLE_ORDER = ["date", "quantity", "unit_price", "revenue", "category", "product", "region", "status"]


def role_candidates(profile: DatasetProfile, role: str) -> list[str]:
    allowed = ROLE_DEFINITIONS[role]["types"]
    return [column.name for column in profile.columns if column.inferred_type in allowed]


def detect_roles(profile: DatasetProfile) -> dict[str, str | None]:
    """Guess which column plays each business role, using names and inferred types."""
    assigned: dict[str, str | None] = {}
    used: set[str] = set()
    for role in ROLE_ORDER:
        definition = ROLE_DEFINITIONS[role]
        candidates = [name for name in role_candidates(profile, role) if name not in used]
        match = None
        for keyword_group in definition["keywords"]:
            for name in candidates:
                tokens = _name_tokens(name)
                if tokens & set(keyword_group):
                    match = name
                    break
            if match:
                break
        if match is None and role == "date" and candidates:
            match = candidates[0]
        assigned[role] = match
        if match:
            used.add(match)
    return assigned


def resolve_roles(profile: DatasetProfile, overrides: dict[str, str] | None) -> dict[str, str | None]:
    """Combine detected roles with user overrides.

    An override of "" switches a role off; a column name assigns it. Overrides
    referring to missing or incompatible columns are ignored.
    """
    roles = detect_roles(profile)
    for role, column in (overrides or {}).items():
        if role not in ROLE_DEFINITIONS:
            continue
        if column == "":
            roles[role] = None
        elif column in role_candidates(profile, role):
            roles[role] = column
    return roles
