from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ErrorBody(Schema):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(Schema):
    error: ErrorBody
