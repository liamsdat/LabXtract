from pathlib import Path
from typing import Iterator, Optional
import re

import pandas as pd


DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")


class RawAnalysisRow(dict):
    """
    {
        "study_name": str | None,
        "analysis_name": str,
        "raw_value": str,
        "study_date": str | None
    }
    """
    pass


class ExcelParser:
    def parse(self, path: str | Path) -> Iterator[RawAnalysisRow]:
        df = pd.read_excel(path, header=None)
        df = df.dropna(how="all")

        current_study: Optional[str] = None

        for _, row in df.iterrows():
            row_values = [
                str(v).strip() for v in row if v is not None and str(v).strip()
            ]

            if not row_values:
                continue

            first_cell = row_values[0]

            if self._is_service_row(first_cell):
                continue

            if self._is_study_name(first_cell):
                current_study = first_cell
                continue

            analysis_name = first_cell

            raw_value = self._extract_result_value(row_values)
            if raw_value is None:
                continue

            study_date = self._extract_date(row_values)

            yield RawAnalysisRow(
                study_name=current_study,
                analysis_name=analysis_name,
                raw_value=raw_value,
                study_date=study_date,
            )

    # ---------- helpers ----------

    @staticmethod
    def _is_service_row(text: str) -> bool:
        service_markers = (
            "лаборатор",
            "исследован",
            "показатель",
            "дата выполн",
            "врач",
        )
        lower = text.lower()
        return any(m in lower for m in service_markers)

    @staticmethod
    def _is_study_name(text: str) -> bool:
        # длинная строка без чисел — название исследования
        if any(c.isdigit() for c in text):
            return False
        return len(text) >= 20

    @staticmethod
    def _extract_date(values: list[str]) -> Optional[str]:
        for v in values:
            if DATE_RE.fullmatch(v):
                return v
        return None

    @staticmethod
    def _extract_result_value(values: list[str]) -> Optional[str]:
        for v in values[1:]:
            if DATE_RE.fullmatch(v):
                continue

            if len(v) > 15:
                continue

            if any(c.isdigit() for c in v) or "+" in v:
                return v

        return None
