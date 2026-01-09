import csv
from pathlib import Path
from typing import Iterable

from models.result import Result

class CSVExporter:
    def __init__(self, delimiter: str = ";", encoding: str = "utf8"):
        self.delimiter = delimiter
        self.encoding = encoding

    def export(self, results: Iterable[Result], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding=self.encoding) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "patient_full_name",
                    "patient_birth_date",
                    "study_name",
                    "analysis_name",
                    "raw_value",
                    "value",
                ],
                delimiter=self.delimiter,
            )
            writer.writeheader()

            for r in results:
                 writer.writerow({
                    "patient_full_name": r.patient.full_name,
                    "patient_birth_date": r.patient.birth_date.isoformat(),
                    "study_name": r.study_name,
                    "analysis_name": r.analysis.name,
                    "raw_value": r.raw_value,
                    "value": r.value,
                })