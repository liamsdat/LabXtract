import re 
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from dateutil.parser import parse as parse_date 


class FilenameParsingError(ValueError):
    """Ошибка парсинга имени файла."""

FILENAME_PATTERN: Final = re.compile(
    r"""
    ^
    (?P<full_name>[А-Яа-яЁё\s\-]+?)      # ФИО
    \s+
    (?P<birth_date>\d{2}\.\d{2}\.\d{4})  # Дата рождения
    \.xlsx$
    """,
    re.VERBOSE,
)

@dataclass(frozen=True)
class ParsedFilename:
    full_name: str
    birth_date: date

def parse_filename(filename: str | Path) -> ParsedFilename:
    name = Path(filename).name

    match = FILENAME_PATTERN.match(name)
    if not match:
        raise FilenameParsingError(
            f"Некорректный формат имени файла: '{name}'"
        )
    
    full_name = match.group("full_name").strip()
    raw_date = match.group("birth_date")

    try:
        birth_date = parse_date(raw_date, dayfirst=True).date()
    except Exception as exc:
        raise FilenameParsingError(
            f"Некорректная дата рождения'{raw_date}'"
        ) from exc

    return ParsedFilename(
        full_name=normalize_full_name(full_name),
        birth_date=birth_date,
    )

def normalize_full_name(full_name: str) -> str:
    parts = [p.capitalize() for p in full_name.split()]
    return " ".join(parts) 