from datetime import date
from enum import Enum   
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.patient import Patient
from models.analysis import Analysis

class ResultStatus(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    UNKNOWN = "unknown"

class Result(BaseModel):
    patient: Patient
    analysis: Analysis

    raw_value: str = Field(
        ...,
        description="Значение из таблицы: "

    )

    value: Optional[float] = Field(
        default=None,
        description="Числовое значение (при удачном извлечении) "

    )

    status: ResultStatus = ResultStatus.UNKNOWN

    study_name: Optional[str] = Field(
        default=None,
        description="Название исследования"

    )

    study_date: Optional[date] = None