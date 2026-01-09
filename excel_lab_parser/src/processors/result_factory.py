from typing import Iterable, Iterator, Optional

from models.patient import Patient
from models.analysis import Analysis, ReferenceRange
from models.result import Result
from processors.normalizer import normalize_value

class ResultFactory:
    def __init__(
        self,
        default_unit: Optional[str] = None,
    ):
        self.default_unit = default_unit
    
    def build_results(
            self,
            patient: Patient,
            raw_rows: Iterable[dict],
    ) -> Iterator[Result]:
        for row in raw_rows:
            analysis = self._build_analysis(row)
            result = self._build_result(patient, analysis, row)
            yield result

    def _build_analysis(self, row: dict) -> Analysis:
        return Analysis(
            name=row["analysis_name"],
            unit=self.default_unit,
            reference_range=ReferenceRange(
                raw_text=None
            ),
        )
    
    def _build_result(
            self,
            patient: Patient,
            analysis: Analysis,
            row: dict,

    ) -> Result:
        raw_value = row["raw_value"]
        value = normalize_value(raw_value)

        return Result(
            patient=patient,
            analysis=analysis,
            raw_value=raw_value,
            value=value,
            study_name=row.get("study_name"),
        )