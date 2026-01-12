"""
Модели данных для LabXtract
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class TestStatus(str, Enum):
    """Статус результата анализа"""
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"
    ABNORMAL = "abnormal"
    NOT_DETECTED = "not_detected"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    SUSPICIOUS = "suspicious"  # Добавим для "Сомнительный"


class TestCategory(str, Enum):
    """Категории анализов"""
    BLOOD_CHEMISTRY = "blood_chemistry"
    HEMATOLOGY = "hematology"
    HORMONES = "hormones"
    URINE = "urine"
    MICROBIOLOGY = "microbiology"
    IMMUNOLOGY = "immunology"
    GENERAL = "general"
    OTHER = "other"


@dataclass
class LabTest:
    """Один лабораторный тест"""
    
    # Основные поля
    name: str
    original_name: str
    
    # Значения
    value: Optional[Union[float, str]] = None
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    original_value: Optional[str] = None
    
    # Метаданные
    unit: Optional[str] = None
    reference_min: Optional[float] = None
    reference_max: Optional[float] = None
    reference_text: Optional[str] = None
    
    # Статус и категория
    status: Optional[TestStatus] = None
    flag: Optional[str] = None  # Оригинальный флаг из файла
    category: Optional[TestCategory] = None
    subcategory: Optional[str] = None
    
    # Даты
    sample_date: Optional[datetime] = None
    result_date: Optional[datetime] = None
    
    # Дополнительно
    doctor: Optional[str] = None
    notes: Optional[str] = None
    
    # Технические поля
    sheet_name: Optional[str] = None  # Добавляем это поле
    row_number: Optional[int] = None  # Добавляем это поле
    file_name: Optional[str] = None
    
    def __post_init__(self):
        """Автоматически заполняем поля после инициализации"""
        # Сохраняем оригинальное значение, если оно не сохранено
        if self.original_value is None and self.value is not None:
            self.original_value = str(self.value)
        
        # Если есть числовое значение, сохраняем его отдельно
        if self.value is not None:
            if isinstance(self.value, (int, float)):
                self.numeric_value = float(self.value)
                self.text_value = None
            else:
                self.text_value = str(self.value)
                self.numeric_value = None
        
        # Определяем статус по флагу
        if self.flag:
            self._determine_status_from_flag()
        
        # Определяем статус по референсному диапазону
        elif self.numeric_value is not None and self.reference_min is not None and self.reference_max is not None:
            self._determine_status_from_reference()
        
        # Автоматически определяем категорию, если не задана
        if self.category is None:
            self._determine_category()
    
    def _determine_status_from_flag(self):
        """Определяет статус из оригинального флага"""
        if not self.flag:
            return
        
        flag_lower = str(self.flag).lower()
        
        if 'норма' in flag_lower or 'normal' in flag_lower:
            self.status = TestStatus.NORMAL
        elif 'повыш' in flag_lower or 'high' in flag_lower or 'повышен' in flag_lower:
            self.status = TestStatus.HIGH
        elif 'пониж' in flag_lower or 'low' in flag_lower or 'понижен' in flag_lower:
            self.status = TestStatus.LOW
        elif 'сомнит' in flag_lower or 'abnormal' in flag_lower:
            self.status = TestStatus.ABNORMAL
        elif 'не обнар' in flag_lower or 'not detected' in flag_lower or 'отрицат' in flag_lower or 'negative' in flag_lower:
            self.status = TestStatus.NOT_DETECTED
        elif 'положит' in flag_lower or 'positive' in flag_lower:
            self.status = TestStatus.POSITIVE
        elif 'сомнит' in flag_lower or 'suspicious' in flag_lower:
            self.status = TestStatus.SUSPICIOUS
    
    def _determine_status_from_reference(self):
        """Определяет статус по референсному диапазону"""
        if self.numeric_value is None or self.reference_min is None or self.reference_max is None:
            return
        
        if self.numeric_value < self.reference_min:
            self.status = TestStatus.LOW
        elif self.numeric_value > self.reference_max:
            self.status = TestStatus.HIGH
        else:
            self.status = TestStatus.NORMAL
    
    def _determine_category(self):
        """Автоматически определяет категорию анализа по названию"""
        name_lower = self.name.lower()
        
        # Гематология
        hematology_keywords = ['гемоглобин', 'лейкоцит', 'эритроцит', 'тромбоцит', 
                               'гематокрит', 'соэ', 'нейтрофил', 'лимфоцит', 'моноцит',
                               'эозинофил', 'базофил', 'hgb', 'wbc', 'rbc', 'plt', 'hct']
        if any(keyword in name_lower for keyword in hematology_keywords):
            self.category = TestCategory.HEMATOLOGY
            return
        
        # Биохимия
        chemistry_keywords = ['глюкоз', 'креатинин', 'мочевин', 'холестерин', 'билирубин',
                             'алт', 'аст', 'ггт', 'щелочн', 'фосфатаз', 'белок', 'альбумин',
                             'липопротеид', 'триглицерид', 'мочев', 'кислот', 'кальци', 'железо']
        if any(keyword in name_lower for keyword in chemistry_keywords):
            self.category = TestCategory.BLOOD_CHEMISTRY
            return
        
        # Гормоны
        hormones_keywords = ['ттг', 'тиреотропн', 'т4', 'т3', 'кортизол', 'инсулин',
                            'пролактин', 'эстрадиол', 'тестостерон', 'прогестерон']
        if any(keyword in name_lower for keyword in hormones_keywords):
            self.category = TestCategory.HORMONES
            return
        
        # Моча
        urine_keywords = ['моч', 'оам', 'урин', 'протеинурия', 'глюкозурия']
        if any(keyword in name_lower for keyword in urine_keywords):
            self.category = TestCategory.URINE
            return
        
        # Микробиология
        micro_keywords = ['микрофлор', 'бактери', 'гриб', 'трихомонад', 'кандид', 
                         'стафилококк', 'стрептококк', 'посев', 'чувствительн']
        if any(keyword in name_lower for keyword in micro_keywords):
            self.category = TestCategory.MICROBIOLOGY
            return
        
        # Иммунология
        immuno_keywords = ['вич', 'гепатит', 'сифилис', 'антител', 'антиген', 'рмп']
        if any(keyword in name_lower for keyword in immuno_keywords):
            self.category = TestCategory.IMMUNOLOGY
            return
        
        self.category = TestCategory.OTHER
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует тест в словарь"""
        result = {
            'name': self.name,
            'original_name': self.original_name,
            'value': self.value,
            'numeric_value': self.numeric_value,
            'text_value': self.text_value,
            'original_value': self.original_value,
            'unit': self.unit,
            'reference_min': self.reference_min,
            'reference_max': self.reference_max,
            'reference_text': self.reference_text,
            'status': self.status.value if self.status else None,
            'flag': self.flag,
            'category': self.category.value if self.category else None,
            'subcategory': self.subcategory,
            'sample_date': self.sample_date.isoformat() if self.sample_date else None,
            'result_date': self.result_date.isoformat() if self.result_date else None,
            'doctor': self.doctor,
            'notes': self.notes,
            'sheet_name': self.sheet_name,
            'row_number': self.row_number,
            'file_name': self.file_name
        }
        
        # Удаляем None значения
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class PatientInfo:
    """Информация о пациенте"""
    
    # Основные поля
    full_name: Optional[str] = None
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    birth_date: Optional[datetime] = None
    
    # Идентификаторы
    patient_id: Optional[str] = None
    medical_record_number: Optional[str] = None
    
    # Контактная информация
    phone: Optional[str] = None
    email: Optional[str] = None
    
    # Дополнительно
    gender: Optional[str] = None
    age: Optional[int] = None
    
    def __post_init__(self):
        """Заполняем поля после инициализации"""
        if self.full_name and not (self.last_name and self.first_name):
            self._parse_full_name()
        
        if self.birth_date:
            self._calculate_age()
    
    def _parse_full_name(self):
        """Парсит полное имя на составляющие"""
        if not self.full_name:
            return
        
        parts = self.full_name.strip().split()
        
        if len(parts) >= 3:
            # Формат: Фамилия Имя Отчество
            self.last_name = parts[0]
            self.first_name = parts[1]
            self.middle_name = ' '.join(parts[2:]) if len(parts) > 2 else None
        elif len(parts) == 2:
            # Формат: Фамилия Имя
            self.last_name = parts[0]
            self.first_name = parts[1]
        elif len(parts) == 1:
            # Только фамилия или имя
            self.last_name = parts[0]
    
    def _calculate_age(self):
        """Рассчитывает возраст по дате рождения"""
        if not self.birth_date:
            return
        
        from datetime import date
        
        today = date.today()
        birth_date = self.birth_date.date()
        
        self.age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    
    def from_sheet_name(self, sheet_name: str) -> bool:
        """
        Извлекает информацию о пациенте из названия листа
        Пример: "Иванов Иван Иванович 25.04.2005"
        """
        if not sheet_name:
            return False
        
        sheet_name = str(sheet_name).strip()
        
        # Удаляем расширение файла если есть
        if sheet_name.endswith('.xlsx') or sheet_name.endswith('.xls'):
            sheet_name = sheet_name.rsplit('.', 1)[0]
        
        # Пробуем разные форматы
        patterns = [
            # Фамилия Имя Отчество ДД.ММ.ГГГГ
            r'^(?P<last_name>[А-ЯЁ][а-яё]+)\s+(?P<first_name>[А-ЯЁ][а-яё]+)\s+(?P<middle_name>[А-ЯЁ][а-яё]+)\s+(?P<birth_date>\d{2}\.\d{2}\.\d{4})$',
            
            # Фамилия Имя ДД.ММ.ГГГГ
            r'^(?P<last_name>[А-ЯЁ][а-яё]+)\s+(?P<first_name>[А-ЯЁ][а-яё]+)\s+(?P<birth_date>\d{2}\.\d{2}\.\d{4})$',
            
            # Любой текст с датой в конце
            r'^(?P<full_name>.+?)\s+(?P<birth_date>\d{2}\.\d{2}\.\d{4})$',
        ]
        
        import re
        from datetime import datetime
        
        for pattern in patterns:
            match = re.match(pattern, sheet_name, re.IGNORECASE)
            if match:
                groups = match.groupdict()
                
                # Если есть полное имя из паттерна
                if 'full_name' in groups:
                    self.full_name = groups['full_name'].strip()
                    self._parse_full_name()
                else:
                    # Собираем из отдельных частей
                    name_parts = []
                    if 'last_name' in groups:
                        name_parts.append(groups['last_name'])
                    if 'first_name' in groups:
                        name_parts.append(groups['first_name'])
                    if 'middle_name' in groups:
                        name_parts.append(groups['middle_name'])
                    
                    if name_parts:
                        self.full_name = ' '.join(name_parts)
                        self._parse_full_name()
                
                # Парсим дату рождения
                birth_date_str = groups.get('birth_date')
                if birth_date_str:
                    try:
                        self.birth_date = datetime.strptime(birth_date_str, '%d.%m.%Y')
                        self._calculate_age()
                    except ValueError:
                        pass
                
                return True
        
        # Если не удалось распарсить по шаблонам, сохраняем как есть
        self.full_name = sheet_name
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует информацию о пациенте в словарь"""
        result = {
            'full_name': self.full_name,
            'last_name': self.last_name,
            'first_name': self.first_name,
            'middle_name': self.middle_name,
            'birth_date': self.birth_date.isoformat() if self.birth_date else None,
            'patient_id': self.patient_id,
            'medical_record_number': self.medical_record_number,
            'phone': self.phone,
            'email': self.email,
            'gender': self.gender,
            'age': self.age
        }
        
        return {k: v for k, v in result.items() if v is not None}


@dataclass
class LabReport:
    """Полный лабораторный отчет"""
    
    # Пациент
    patient: PatientInfo
    
    # Анализы
    tests: List[LabTest] = field(default_factory=list)
    
    # Метаданные отчета
    report_date: Optional[datetime] = None
    laboratory_name: Optional[str] = None
    doctor_in_charge: Optional[str] = None
    
    # Техническая информация
    source_file: Optional[str] = None
    sheet_name: Optional[str] = None
    extraction_date: datetime = field(default_factory=datetime.now)
    
    # Статистика
    total_tests: int = 0
    abnormal_tests: int = 0
    
    def __post_init__(self):
        """Заполняем статистику"""
        self.total_tests = len(self.tests)
        abnormal_statuses = [TestStatus.HIGH, TestStatus.LOW, TestStatus.ABNORMAL, TestStatus.SUSPICIOUS]
        self.abnormal_tests = len([
            t for t in self.tests 
            if t.status in abnormal_statuses
        ])
    
    def add_test(self, test: LabTest):
        """Добавляет тест в отчет"""
        self.tests.append(test)
        self.total_tests += 1
        
        abnormal_statuses = [TestStatus.HIGH, TestStatus.LOW, TestStatus.ABNORMAL, TestStatus.SUSPICIOUS]
        if test.status in abnormal_statuses:
            self.abnormal_tests += 1
    
    def get_tests_by_category(self, category: TestCategory) -> List[LabTest]:
        """Возвращает тесты по категории"""
        return [test for test in self.tests if test.category == category]
    
    def get_abnormal_tests(self) -> List[LabTest]:
        """Возвращает только аномальные тесты"""
        abnormal_statuses = [TestStatus.HIGH, TestStatus.LOW, TestStatus.ABNORMAL, TestStatus.SUSPICIOUS]
        return [test for test in self.tests if test.status in abnormal_statuses]
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует отчет в словарь"""
        return {
            'patient': self.patient.to_dict(),
            'tests': [test.to_dict() for test in self.tests],
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'laboratory_name': self.laboratory_name,
            'doctor_in_charge': self.doctor_in_charge,
            'source_file': self.source_file,
            'sheet_name': self.sheet_name,
            'extraction_date': self.extraction_date.isoformat(),
            'total_tests': self.total_tests,
            'abnormal_tests': self.abnormal_tests
        }
    
    def to_dataframe(self):
        """Преобразует отчет в pandas DataFrame"""
        import pandas as pd
        
        if not self.tests:
            return pd.DataFrame()
        
        # Собираем данные тестов
        test_data = [test.to_dict() for test in self.tests]
        
        # Добавляем информацию о пациенте в каждый тест
        for data in test_data:
            data.update({
                'patient_full_name': self.patient.full_name,
                'patient_birth_date': self.patient.birth_date.isoformat() if self.patient.birth_date else None,
                'patient_age': self.patient.age,
                'source_file': self.source_file,
                'sheet_name': self.sheet_name,
                'report_date': self.report_date.isoformat() if self.report_date else None,
                'laboratory_name': self.laboratory_name,
                'doctor_in_charge': self.doctor_in_charge,
            })
        
        return pd.DataFrame(test_data)