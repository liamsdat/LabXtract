"""
Валидатор данных лабораторных анализов
Проверяет корректность извлеченных данных
"""

import re
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, date
import logging

from .models import LabTest, LabReport, TestStatus, TestCategory

logger = logging.getLogger(__name__)


class DataValidator:
    """Валидатор медицинских данных"""
    
    # Диапазоны нормальных значений для распространенных анализов
    REFERENCE_RANGES = {
        'Гемоглобин': {'min': 120, 'max': 160, 'unit': 'г/л', 'gender_specific': True},
        'Лейкоциты': {'min': 4.0, 'max': 9.0, 'unit': '10⁹/л'},
        'Эритроциты': {'min': 3.9, 'max': 5.5, 'unit': '10¹²/л', 'gender_specific': True},
        'Тромбоциты': {'min': 150, 'max': 400, 'unit': '10⁹/л'},
        'Глюкоза': {'min': 3.9, 'max': 6.1, 'unit': 'ммоль/л'},
        'Креатинин': {'min': 58, 'max': 110, 'unit': 'мкмоль/л', 'gender_specific': True},
        'Мочевина': {'min': 2.8, 'max': 7.2, 'unit': 'ммоль/л'},
        'Холестерин': {'min': 3.6, 'max': 6.2, 'unit': 'ммоль/л'},
        'АЛТ': {'min': 0, 'max': 35, 'unit': 'Ед/л', 'gender_specific': True},
        'АСТ': {'min': 0, 'max': 35, 'unit': 'Ед/л', 'gender_specific': True},
        'ТТГ': {'min': 0.4, 'max': 4.0, 'unit': 'мкЕд/мл'},
    }
    
    # Допустимые единицы измерения для каждого типа анализа
    ALLOWED_UNITS = {
        'Гемоглобин': ['г/л', 'g/l', 'г/дл', 'g/dl'],
        'Лейкоциты': ['10⁹/л', '10^9/л', '*10^9/л', 'тыс/мкл'],
        'Эритроциты': ['10¹²/л', '10^12/л', '*10^12/л', 'млн/мкл'],
        'Тромбоциты': ['10⁹/л', '10^9/л', '*10^9/л', 'тыс/мкл'],
        'Глюкоза': ['ммоль/л', 'моль/л', 'mg/dl', 'мг/дл'],
        'Креатинин': ['мкмоль/л', 'μmol/l', 'mg/dl', 'мг/дл'],
        'Мочевина': ['ммоль/л', 'моль/л', 'mg/dl', 'мг/дл'],
        'Холестерин': ['ммоль/л', 'моль/л', 'mg/dl', 'мг/дл'],
        'АЛТ': ['Ед/л', 'U/l', 'МЕ/л', 'IU/l'],
        'АСТ': ['Ед/л', 'U/l', 'МЕ/л', 'IU/l'],
        'ТТГ': ['мкЕд/мл', 'μIU/ml', 'мМЕ/л', 'mIU/l'],
    }
    
    # Паттерны для валидации значений
    VALUE_PATTERNS = {
        'numeric': r'^[-+]?\d*\.?\d+$',
        'percentage': r'^\d*\.?\d+\s*%$',
        'range': r'^\d*\.?\d+\s*[-–]\s*\d*\.?\d+$',
        'date': r'^\d{2}[\.\/-]\d{2}[\.\/-]\d{2,4}$',
    }
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.validation_errors = []
        self.validation_warnings = []
        
    def validate_test(self, test: LabTest) -> Dict:
        """
        Валидирует один лабораторный тест
        
        Returns:
            Словарь с результатами валидации
        """
        errors = []
        warnings = []
        
        # 1. Проверяем название теста
        name_validation = self._validate_test_name(test.name, test.original_name)
        errors.extend(name_validation['errors'])
        warnings.extend(name_validation['warnings'])
        
        # 2. Проверяем значение
        if test.numeric_value is not None:
            value_validation = self._validate_numeric_value(test.name, test.numeric_value)
        elif test.text_value is not None:
            value_validation = self._validate_text_value(test.name, test.text_value)
        else:
            value_validation = self._validate_missing_value(test.name)
        
        errors.extend(value_validation['errors'])
        warnings.extend(value_validation['warnings'])
        
        # 3. Проверяем единицы измерения
        if test.unit:
            unit_validation = self._validate_unit(test.name, test.unit)
            errors.extend(unit_validation['errors'])
            warnings.extend(unit_validation['warnings'])
        
        # 4. Проверяем референсный диапазон
        if test.reference_min is not None and test.reference_max is not None:
            range_validation = self._validate_reference_range(
                test.name, test.reference_min, test.reference_max
            )
            errors.extend(range_validation['errors'])
            warnings.extend(range_validation['warnings'])
        
        # 5. Проверяем статус
        if test.status:
            status_validation = self._validate_status(test)
            errors.extend(status_validation['errors'])
            warnings.extend(status_validation['warnings'])
        
        # 6. Проверяем даты
        if test.sample_date:
            date_validation = self._validate_date(test.sample_date, 'sample_date')
            errors.extend(date_validation['errors'])
            warnings.extend(date_validation['warnings'])
        
        if test.result_date:
            date_validation = self._validate_date(test.result_date, 'result_date')
            errors.extend(date_validation['errors'])
            warnings.extend(date_validation['warnings'])
        
        # 7. Проверяем логические несоответствия
        logic_validation = self._validate_test_logic(test)
        errors.extend(logic_validation['errors'])
        warnings.extend(logic_validation['warnings'])
        
        # Запоминаем ошибки и предупреждения
        self.validation_errors.extend(errors)
        self.validation_warnings.extend(warnings)
        
        return {
            'is_valid': len(errors) == 0,
            'has_warnings': len(warnings) > 0,
            'errors': errors,
            'warnings': warnings,
            'test_name': test.name,
            'test_id': id(test),
        }
    
    def validate_report(self, report: LabReport) -> Dict:
        """
        Валидирует весь отчет
        
        Returns:
            Словарь с результатами валидации
        """
        errors = []
        warnings = []
        
        # 1. Проверяем информацию о пациенте
        patient_validation = self._validate_patient_info(report.patient)
        errors.extend(patient_validation['errors'])
        warnings.extend(patient_validation['warnings'])
        
        # 2. Проверяем каждый тест в отчете
        test_results = []
        valid_tests = 0
        invalid_tests = 0
        
        for test in report.tests:
            test_validation = self.validate_test(test)
            test_results.append(test_validation)
            
            if test_validation['is_valid']:
                valid_tests += 1
            else:
                invalid_tests += 1
        
        # 3. Проверяем целостность отчета
        integrity_validation = self._validate_report_integrity(report)
        errors.extend(integrity_validation['errors'])
        warnings.extend(integrity_validation['warnings'])
        
        # 4. Проверяем дубликаты тестов
        duplicate_validation = self._check_duplicate_tests(report.tests)
        warnings.extend(duplicate_validation['warnings'])
        
        # Собираем все ошибки и предупреждения из тестов
        all_test_errors = []
        all_test_warnings = []
        
        for result in test_results:
            all_test_errors.extend(result['errors'])
            all_test_warnings.extend(result['warnings'])
        
        errors.extend(all_test_errors)
        warnings.extend(all_test_warnings)
        
        return {
            'is_valid': len(errors) == 0,
            'has_warnings': len(warnings) > 0,
            'total_tests': len(report.tests),
            'valid_tests': valid_tests,
            'invalid_tests': invalid_tests,
            'patient_errors': patient_validation['errors'],
            'patient_warnings': patient_validation['warnings'],
            'test_results': test_results,
            'errors': errors,
            'warnings': warnings,
            'report_date': report.report_date,
            'source_file': report.source_file,
        }
    
    def _validate_test_name(self, name: str, original_name: str) -> Dict:
        """Валидирует название теста"""
        errors = []
        warnings = []
        
        if not name or not name.strip():
            errors.append('Название теста не может быть пустым')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем длину названия
        if len(name) > 200:
            warnings.append(f'Название теста слишком длинное: {len(name)} символов')
        
        # Проверяем наличие недопустимых символов
        invalid_chars = re.findall(r'[^\w\s\-\.\(\)\/%,]', name)
        if invalid_chars:
            unique_chars = set(invalid_chars)
            warnings.append(f'Название содержит нестандартные символы: {", ".join(unique_chars)}')
        
        # Проверяем, является ли название известным тестом
        if name not in self.REFERENCE_RANGES:
            warnings.append(f'Неизвестный тест: {name}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_numeric_value(self, test_name: str, value: float) -> Dict:
        """Валидирует числовое значение"""
        errors = []
        warnings = []
        
        # Проверяем, что значение не NaN или бесконечность
        if not isinstance(value, (int, float)):
            errors.append(f'Некорректный тип числового значения: {type(value)}')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем, что значение не NaN
        import math
        if math.isnan(value):
            errors.append('Значение является NaN')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем, что значение не бесконечность
        if math.isinf(value):
            errors.append('Значение бесконечно')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем диапазон значения
        if test_name in self.REFERENCE_RANGES:
            ref_range = self.REFERENCE_RANGES[test_name]
            
            # Проверяем физиологически возможные значения
            if value < 0:
                warnings.append('Отрицательное значение может быть ошибкой')
            
            # Проверяем экстремальные значения
            extreme_threshold = ref_range.get('max', 100) * 10
            if value > extreme_threshold:
                warnings.append(f'Экстремально высокое значение: {value}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_text_value(self, test_name: str, value: str) -> Dict:
        """Валидирует текстовое значение"""
        errors = []
        warnings = []
        
        if not value or not value.strip():
            errors.append('Текстовое значение не может быть пустым')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем длину текстового значения
        if len(value) > 500:
            warnings.append(f'Текстовое значение слишком длинное: {len(value)} символов')
        
        # Проверяем допустимые текстовые значения для известных тестов
        allowed_text_values = {
            'Trichomonas vaginalis': ['Не обнаружено', 'Обнаружено', 'Положительный', 'Отрицательный'],
            'Candida': ['Не обнаружено', 'Обнаружено', 'Положительный', 'Отрицательный'],
            'Микрофлора': ['Не обнаружено', 'Скудно', 'Умеренно', 'Обильно'],
            'Слизь': ['Не обнаружено', '+', '++', '+++'],
        }
        
        if test_name in allowed_text_values:
            if value not in allowed_text_values[test_name]:
                warnings.append(f'Необычное текстовое значение для {test_name}: {value}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_missing_value(self, test_name: str) -> Dict:
        """Валидирует отсутствие значения"""
        errors = []
        warnings = []
        
        warnings.append(f'Отсутствует значение для теста: {test_name}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_unit(self, test_name: str, unit: str) -> Dict:
        """Валидирует единицы измерения"""
        errors = []
        warnings = []
        
        if not unit or not unit.strip():
            errors.append('Единицы измерения не могут быть пустыми')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем, разрешены ли такие единицы для данного теста
        if test_name in self.ALLOWED_UNITS:
            allowed_units = self.ALLOWED_UNITS[test_name]
            unit_normalized = unit.strip().lower()
            allowed_normalized = [u.lower() for u in allowed_units]
            
            if unit_normalized not in allowed_normalized:
                warnings.append(f'Нестандартные единицы измерения для {test_name}: {unit}. '
                               f'Ожидались: {", ".join(allowed_units)}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_reference_range(self, test_name: str, min_val: float, max_val: float) -> Dict:
        """Валидирует референсный диапазон"""
        errors = []
        warnings = []
        
        # Проверяем, что min <= max
        if min_val > max_val:
            errors.append(f'Минимальное значение ({min_val}) больше максимального ({max_val})')
        
        # Проверяем, что значения не отрицательные (если не проценты)
        if min_val < 0 or max_val < 0:
            warnings.append('Отрицательные значения в референсном диапазоне')
        
        # Проверяем, соответствует ли диапазон ожидаемому для теста
        if test_name in self.REFERENCE_RANGES:
            expected_range = self.REFERENCE_RANGES[test_name]
            expected_min = expected_range.get('min')
            expected_max = expected_range.get('max')
            
            if expected_min is not None and expected_max is not None:
                # Проверяем, не слишком ли отличается от ожидаемого
                min_diff = abs(min_val - expected_min) / expected_min
                max_diff = abs(max_val - expected_max) / expected_max
                
                if min_diff > 0.5 or max_diff > 0.5:  # Более 50% отклонение
                    warnings.append(f'Необычный референсный диапазон для {test_name}: '
                                   f'{min_val}-{max_val}. Ожидался: {expected_min}-{expected_max}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_status(self, test: LabTest) -> Dict:
        """Валидирует статус теста"""
        errors = []
        warnings = []
        
        if not test.status:
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем соответствие статуса и значения
        if test.numeric_value is not None and test.reference_min is not None and test.reference_max is not None:
            expected_status = TestStatus.NORMAL
            
            if test.numeric_value < test.reference_min:
                expected_status = TestStatus.LOW
            elif test.numeric_value > test.reference_max:
                expected_status = TestStatus.HIGH
            
            if test.status != expected_status:
                warnings.append(f'Несоответствие статуса: ожидался {expected_status.value}, '
                               f'получен {test.status.value}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_date(self, date_obj: datetime, date_type: str) -> Dict:
        """Валидирует дату"""
        errors = []
        warnings = []
        
        if not isinstance(date_obj, datetime):
            errors.append(f'Некорректный тип даты {date_type}: {type(date_obj)}')
            return {'errors': errors, 'warnings': warnings}
        
        # Проверяем, что дата не в будущем (для дат образцов и результатов)
        today = datetime.now()
        if date_obj > today:
            warnings.append(f'Дата {date_type} в будущем: {date_obj.strftime("%d.%m.%Y")}')
        
        # Проверяем, что дата не слишком старая (старше 100 лет)
        hundred_years_ago = today.replace(year=today.year - 100)
        if date_obj < hundred_years_ago:
            warnings.append(f'Дата {date_type} слишком старая: {date_obj.strftime("%d.%m.%Y")}')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_test_logic(self, test: LabTest) -> Dict:
        """Проверяет логические несоответствия в тесте"""
        errors = []
        warnings = []
        
        # Проверяем, что если есть числовое значение, должны быть единицы измерения
        if test.numeric_value is not None and not test.unit:
            warnings.append('Числовое значение без единиц измерения')
        
        # Проверяем, что если есть референсный диапазон, должны быть единицы измерения
        if (test.reference_min is not None or test.reference_max is not None) and not test.unit:
            warnings.append('Референсный диапазон без единиц измерения')
        
        # Проверяем, что дата результата не раньше даты взятия образца
        if test.sample_date and test.result_date:
            if test.result_date < test.sample_date:
                warnings.append('Дата результата раньше даты взятия образца')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_patient_info(self, patient) -> Dict:
        """Валидирует информацию о пациенте"""
        errors = []
        warnings = []
        
        # Проверяем ФИО
        if not patient.full_name or not patient.full_name.strip():
            warnings.append('Отсутствует ФИО пациента')
        else:
            # Проверяем формат ФИО (должно быть минимум 2 слова)
            name_parts = patient.full_name.strip().split()
            if len(name_parts) < 2:
                warnings.append(f'Неполное ФИО: {patient.full_name}')
        
        # Проверяем дату рождения
        if patient.birth_date:
            # Проверяем, что дата рождения не в будущем
            if patient.birth_date > datetime.now():
                errors.append('Дата рождения в будущем')
            
            # Проверяем возраст
            if patient.age is not None:
                if patient.age < 0:
                    errors.append('Отрицательный возраст')
                elif patient.age > 120:
                    warnings.append(f'Необычно большой возраст: {patient.age} лет')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_report_integrity(self, report: LabReport) -> Dict:
        """Проверяет целостность отчета"""
        errors = []
        warnings = []
        
        # Проверяем, что в отчете есть тесты
        if not report.tests:
            errors.append('Отчет не содержит тестов')
        
        # Проверяем дату отчета
        if not report.report_date:
            warnings.append('Отсутствует дата отчета')
        elif report.report_date > datetime.now():
            warnings.append('Дата отчета в будущем')
        
        # Проверяем источник файла
        if not report.source_file:
            warnings.append('Отсутствует информация об исходном файле')
        
        return {'errors': errors, 'warnings': warnings}
    
    def _check_duplicate_tests(self, tests: List[LabTest]) -> Dict:
        """Проверяет дубликаты тестов"""
        warnings = []
        
        # Группируем тесты по названию
        test_groups = {}
        for test in tests:
            if test.name not in test_groups:
                test_groups[test.name] = []
            test_groups[test.name].append(test)
        
        # Проверяем группы с более чем одним тестом
        for test_name, test_list in test_groups.items():
            if len(test_list) > 1:
                warnings.append(f'Найдено {len(test_list)} дубликатов теста: {test_name}')
                
                # Проверяем, различаются ли значения
                values = []
                for test in test_list:
                    if test.numeric_value is not None:
                        values.append(test.numeric_value)
                    elif test.text_value is not None:
                        values.append(test.text_value)
                
                if len(set(values)) > 1:
                    warnings.append(f'Дубликаты теста {test_name} имеют разные значения')
        
        return {'errors': [], 'warnings': warnings}
    
    def get_validation_summary(self) -> Dict:
        """Возвращает сводку по валидации"""
        return {
            'total_errors': len(self.validation_errors),
            'total_warnings': len(self.validation_warnings),
            'errors_by_type': self._group_by_type(self.validation_errors),
            'warnings_by_type': self._group_by_type(self.validation_warnings),
        }
    
    def _group_by_type(self, items: List[str]) -> Dict[str, int]:
        """Группирует ошибки/предупреждения по типу"""
        groups = {}
        
        for item in items:
            # Определяем тип по первому слову или ключевым словам
            if 'название' in item.lower():
                groups['name'] = groups.get('name', 0) + 1
            elif 'значение' in item.lower() or 'число' in item.lower():
                groups['value'] = groups.get('value', 0) + 1
            elif 'единиц' in item.lower() or 'unit' in item.lower():
                groups['unit'] = groups.get('unit', 0) + 1
            elif 'диапазон' in item.lower() or 'норма' in item.lower():
                groups['range'] = groups.get('range', 0) + 1
            elif 'дата' in item.lower() or 'date' in item.lower():
                groups['date'] = groups.get('date', 0) + 1
            elif 'статус' in item.lower() or 'status' in item.lower():
                groups['status'] = groups.get('status', 0) + 1
            elif 'пациент' in item.lower() or 'patient' in item.lower():
                groups['patient'] = groups.get('patient', 0) + 1
            else:
                groups['other'] = groups.get('other', 0) + 1
        
        return groups
    
    def clear(self):
        """Очищает накопленные ошибки и предупреждения"""
        self.validation_errors = []
        self.validation_warnings = []