from datetime import date

from models.patient import Patient # type: ignore
from processors.result_factory import ResultFactory # type: ignore

def test_result_factory_numeric_value():
    patient = Patient(
        full_name="Иванов Серёга",
        birth_date=date(1999, 1, 1),
    )

    raw_rows = [
        {
            "study_name": "Общий анализ крови",
            "analysis_name": "Лейкоциты",
            "raw_value": "12",
        }
    ]

    factory = ResultFactory()
    results = list(factory.build_results(patient, raw_rows))

    assert len(results) == 1

    result = results[0]

    assert result.patient == patient
    assert result.analysis.name == "Лейкоциты"
    assert result.raw_value == "12"
    assert result.value == 12.0
    assert result.study_name == "Общий анализ крови"

def test_result_factory_non_numeric_value():
    patient = Patient(
        full_name="Петров ПетровПетров",
        birth_date=date(2012, 12, 12),
    )

    raw_rows = [
        {
            "study_name": "Микроскопия мазка",
            "analysis_name": "Эритроциты",
            "raw_value": "единичные",
        }
    ]

    factory = ResultFactory()
    results = list(factory.build_results(patient, raw_rows))

    result = results[0]

    assert result.value is None
    assert result.raw_value == "единичные"

def test_result_factory_multiple_rows():
    patient = Patient(
        full_name="Тестов Тест",
        birth_date=date(1200, 3, 15),
    )

    raw_rows = [
        {
            "study_name": "Исследование 1",
            "analysis_name": "Анализ А",
            "raw_value": "5",
        },
        {
           "study_name": "Исследование 1",
            "analysis_name": "Анализ В",
            "raw_value": "не обнаружено", 
        }
    ]

    factory = ResultFactory()
    results = list(factory.build_results(patient, raw_rows))

    assert len(results) == 2
    assert results[0].value == 5.0
    assert results[1].value is None 