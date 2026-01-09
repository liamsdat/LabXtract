from pathlib import Path

from parsers.filename_parser import parse_filename
from parsers.excel_parser import ExcelParser
from processors.result_factory import ResultFactory
from exporters.csv_exporter import CSVExporter
from models.patient import Patient


def main() -> None:
    input_dir = Path("data/input")
    output_dir = Path("data/output")

    if not input_dir.exists():
        raise FileNotFoundError(
            f"Папка с входными файлами не найдена: {input_dir.resolve()}"
        )

    excel_parser = ExcelParser()
    result_factory = ResultFactory()
    csv_exporter = CSVExporter()

    all_results = []

    for file_path in input_dir.glob("*.xlsx"):
        print("=" * 80)
        print(f"File exist: {file_path.name}")

        # 1️⃣ Парсинг имени файла
        parsed = parse_filename(file_path.name)
        patient = Patient(
            full_name=parsed.full_name,
            birth_date=parsed.birth_date,
        )

        print(f"Пациент: {patient.full_name}, {patient.birth_date}")

        # 2️⃣ Excel → сырые строки
        raw_rows = excel_parser.parse(file_path)

        # 3️⃣ Сборка Result
        results = list(
            result_factory.build_results(patient, raw_rows)
        )

        if not results:
            print("Анализы не найдены")
            continue

        all_results.extend(results)

        # Временный вывод в консоль
        for r in results:
            print(
                f"{r.analysis.name:<25} | "
                f"{r.raw_value:<15} | "
                f"{str(r.value):<6} | "
                f"{r.study_name}"
            )

    # 4️⃣ CSV-экспорт
    if all_results:
        output_file = output_dir / "lab_results.csv"
        csv_exporter.export(all_results, output_file)
        print("=" * 80)
        print(f"CSV сохранён: {output_file.resolve()}")
    else:
        print("Нет данных для экспорта")


if __name__ == "__main__":
    main()
