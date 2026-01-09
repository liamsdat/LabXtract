from datetime import date
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

class Patient(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    full_name: str = Field(..., min_length=3)
    birth_date: date

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if len(value.split()) < 2:
            raise ValueError("ФИО должно содержать минимум имя и фамилию")

        return value
    
    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Путешественник во времени?")
        return value

    @property
    def age(self) -> int:
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - (
                (today.month, today.day)
                < (self.birth_date.month, self.birth_date.day)
            )
        )