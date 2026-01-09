from typing import Optional
from pydantic import BaseModel, Field, field_validator

class ReferenceRange(BaseModel):
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    raw_value: Optional[float] = None

    @field_validator("max_value")
    @classmethod
    def validate_range(cls, max_value, info):
        min_value = info.data.get("min_value")
        if (
            min_value is not None
            and max_value is not None
            and max_value < min_value
        ):
            raise ValueError("max_value меньше min_value")
        return max_value
    

class Analysis(BaseModel):
    name: str = Field(..., min_length=2)
    unit: Optional[str] = None
    reference_range: ReferenceRange

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()