"""
Excel парсер для лабораторных анализов
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import re
from datetime import datetime
import logging

from ..core.models import LabTest, PatientInfo, LabReport, TestStatus, TestCategory

logger = logging.getLogger(__name__)


class ExcelLabParser:
    """Парсер Excel файлов с медицинскими анализами"""
    
    # Ключевые слова для поиска заголовков
    HEADER_KEYWORDS = {
        'test_name': ['показатель', 'анализ', 'название', 'test', 'parameter'],
        'result': ['результат', 'значение', 'value', 'уровень', 'level'],
        'unit': ['ед.изм', 'единиц', 'unit', 'измерен', 'measure'],
        'reference': ['норма', 'референс', 'reference', 'диапазон', 'range'],
        'flag': ['флаг', 'flag', 'статус', 'status'],
        'date_sample': ['дата взятия', 'дата исслед', 'sample date', 'collection'],
        'date_result': ['дата выполн', 'дата результата', 'result date', 'report date'],
        'doctor': ['врач', 'doctor', 'исполнитель', 'executor']
    }
    
    # Категории анализов и их ключевые слова
    TEST_CATEGORIES = {
        TestCategory.HEMATOLOGY: [
            'гемоглобин', 'лейкоциты', 'эритроциты', 'тромбоциты',
            'гематокрит', 'соэ', 'нейтрофилы', 'лимфоциты',
            'моноциты', 'эозинофилы', 'базофилы', 'hgb', 'wbc',
            'rbc', 'plt', 'hct', 'esr'
        ],
        TestCategory.BLOOD_CHEMISTRY: [
            'глюкоза', 'креатинин', 'мочевина', 'холестерин',
            'биллирубин', 'алт', 'аст', 'ггт', 'щелочная фосфатаза',
            'белок', 'альбумин', 'глобулин', 'липопротеиды',
            'триглицериды', 'мочевая кислота', 'глюк', 'crea',
            'urea', 'chol', 'alt', 'ast', 'bilirubin'
        ],
        TestCategory.HORMONES: [
            'ттг', 'тиреотропный', 'т4', 'т3', 'кортизол',
            'инсулин', 'пролактин', 'эстрадиол', 'тестостерон',
            'прогестерон', 'лг', 'фсг', 'тsh', 'thyroid'
        ],
        TestCategory.URINE: [
            'моча', 'оам', 'белок', 'глюкоза', 'кетоны',
            'билирубин', 'уробилиноген', 'нитриты', 'лейкоциты',
            'эритроциты', 'цилиндры', 'эпителий', 'соли',
            'urine', 'protein', 'glucose', 'ketones'
        ],
        TestCategory.MICROBIOLOGY: [
            'микрофлора', 'бактерии', 'грибы', 'трихомонады',
            'кандида', 'стафилококк', 'стрептококк', 'посев',
            'чувствительность', 'culture', 'sensitivity'
        ],
        TestCategory.IMMUNOLOGY: [
            'вич', 'гепатит', 'сифилис', 'антитела', 'антиген',
            'рмп', 'hbsag', 'anti-hcv', 'hiv', 'hepatitis',
            'syphilis', 'antibody', 'antigen'
        ]
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.current_category = None
        self.current_subcategory = None
        
    def parse_file(self, file_path: Path) -> List[LabReport]:
        """
        Парсит Excel файл и возвращает список отчетов
        (по одному на каждый лист)
        """
        reports = []
        
        try:
            # Читаем Excel файл
            excel_file = pd.ExcelFile(file_path)
            logger.info(f"Открыт файл: {file_path}, листов: {len(excel_file.sheet_names)}")
            
            # Обрабатываем каждый лист
            for sheet_name in excel_file.sheet_names:
                logger.info(f"Обработка листа: {sheet_name}")
                
                # Парсим лист
                df = excel_file.parse(sheet_name, header=None, dtype=str)
                report = self._parse_sheet(df, sheet_name, file_path.name)
                
                if report and report.tests:
                    reports.append(report)
                    logger.info(f"  Извлечено тестов: {len(report.tests)}")
                else:
                    logger.warning(f"  Не удалось извлечь данные из листа: {sheet_name}")
            
            return reports
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге файла {file_path}: {e}")
            raise
    
    def _parse_sheet(self, df: pd.DataFrame, sheet_name: str, filename: str) -> Optional[LabReport]:
        """Парсит один лист Excel"""
        # Извлекаем информацию о пациенте из названия листа
        patient = PatientInfo()
        patient.from_sheet_name(sheet_name)
        
        # Создаем отчет
        report = LabReport(
            patient=patient,
            source_file=filename,
            sheet_name=sheet_name,
            report_date=datetime.now()
        )
        
        # Ищем таблицу с данными
        table_data = self._find_and_parse_table(df)
        if not table_data:
            return None
        
        # Преобразуем данные в тесты
        for test_data in table_data:
            test = self._create_test_from_data(test_data, sheet_name)
            if test:
                report.add_test(test)
        
        return report
    
    def _find_and_parse_table(self, df: pd.DataFrame) -> List[Dict]:
        """Находит и парсит таблицу с анализами"""
        data = []
        
        # Ищем заголовок таблицы
        header_row_idx = self._find_header_row(df)
        if header_row_idx is None:
            return data
        
        # Определяем столбцы
        columns = self._identify_columns(df.iloc[header_row_idx])
        if not columns:
            return data
        
        logger.debug(f"Найдена таблица в строке {header_row_idx}, столбцы: {columns}")
        
        # Парсим строки таблицы
        for row_idx in range(header_row_idx + 1, len(df)):
            row = df.iloc[row_idx]
            
            # Пропускаем пустые строки
            if self._is_empty_row(row):
                continue
            
            # Определяем, что это за строка
            test_name = self._get_cell_value(row, columns.get('test_name'))
            
            # Если строка похожа на заголовок категории
            if test_name and not self._looks_like_test(test_name):
                self._update_category(test_name)
                continue
            
            # Парсим строку с тестом
            test_data = self._parse_test_row(row, columns, row_idx)
            if test_data:
                test_data['category'] = self.current_category
                test_data['subcategory'] = self.current_subcategory
                data.append(test_data)
        
        return data
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """Находит строку с заголовками таблицы"""
        for i in range(min(20, len(df))):  # Проверяем первые 20 строк
            row = df.iloc[i]
            row_text = ' '.join(str(cell).lower() for cell in row.dropna())
            
            # Проверяем наличие ключевых слов
            has_test_name = any(kw in row_text for kw in self.HEADER_KEYWORDS['test_name'])
            has_result = any(kw in row_text for kw in self.HEADER_KEYWORDS['result'])
            has_unit = any(kw in row_text for kw in self.HEADER_KEYWORDS['unit'])
            
            if has_test_name and (has_result or has_unit):
                return i
        
        return None
    
    def _identify_columns(self, header_row: pd.Series) -> Dict[str, int]:
        """Определяет назначение столбцов"""
        columns = {}
        
        for col_idx, cell in enumerate(header_row):
            if pd.isna(cell):
                continue
            
            cell_text = str(cell).lower()
            
            # Ищем ключевые слова
            for column_type, keywords in self.HEADER_KEYWORDS.items():
                if any(keyword in cell_text for keyword in keywords):
                    if column_type not in columns:  # Берем первое совпадение
                        columns[column_type] = col_idx
                    break
        
        return columns
    
    def _is_empty_row(self, row: pd.Series) -> bool:
        """Проверяет, пустая ли строка"""
        return all(pd.isna(cell) or str(cell).strip() == '' for cell in row)
    
    def _looks_like_test(self, text: str) -> bool:
        """Определяет, похож ли текст на название теста"""
        if not text:
            return False
        
        text_lower = str(text).lower().strip()
        
        # Игнорируем общие заголовки
        ignore_patterns = [
            'лабораторные', 'исследование', 'анализ крови',
            'общий анализ', 'биохимический', 'гормональный'
        ]
        
        if any(pattern in text_lower for pattern in ignore_patterns):
            return False
        
        # Проверяем, является ли это известным тестом
        for category, tests in self.TEST_CATEGORIES.items():
            if any(test in text_lower for test in tests):
                return True
        
        # Эвристика: короткие названия (1-5 слов) обычно являются тестами
        words = text_lower.split()
        if 1 <= len(words) <= 5:
            # Проверяем, не содержит ли это слов "исследование", "анализ" в конце
            if not text_lower.endswith(('исследование', 'анализ', 'тест')):
                return True
        
        return False
    
    def _update_category(self, category_name: str):
        """Обновляет текущую категорию и подкатегорию"""
        category_name = str(category_name).strip()
        
        # Определяем категорию по ключевым словам
        for category_type, keywords in self.TEST_CATEGORIES.items():
            if any(keyword in category_name.lower() for keyword in keywords):
                self.current_category = category_type
                break
        else:
            self.current_category = TestCategory.OTHER
        
        self.current_subcategory = category_name
    
    def _get_cell_value(self, row: pd.Series, col_idx: Optional[int]) -> Optional[str]:
        """Безопасно получает значение ячейки"""
        if col_idx is None or col_idx >= len(row):
            return None
        
        value = row.iloc[col_idx]
        if pd.isna(value):
            return None
        
        return str(value).strip()
    
    def _parse_test_row(self, row: pd.Series, columns: Dict, row_idx: int) -> Optional[Dict]:
        """Парсит строку с тестом"""
        test_name = self._get_cell_value(row, columns.get('test_name'))
        if not test_name:
            return None
        
        # Извлекаем значения
        result_value = self._get_cell_value(row, columns.get('result'))
        unit_value = self._get_cell_value(row, columns.get('unit'))
        reference_value = self._get_cell_value(row, columns.get('reference'))
        flag_value = self._get_cell_value(row, columns.get('flag'))
        date_sample_value = self._get_cell_value(row, columns.get('date_sample'))
        date_result_value = self._get_cell_value(row, columns.get('date_result'))
        doctor_value = self._get_cell_value(row, columns.get('doctor'))
        
        # Парсим числовое значение
        numeric_value, text_value = self._parse_result_value(result_value)
        
        # Парсим референсный диапазон
        ref_min, ref_max, ref_text = self._parse_reference_range(reference_value)
        
        # Парсим даты
        sample_date = self._parse_date(date_sample_value)
        result_date = self._parse_date(date_result_value)
        
        return {
            'original_name': test_name,
            'value': result_value,
            'numeric_value': numeric_value,
            'text_value': text_value,
            'unit': unit_value,
            'reference_min': ref_min,
            'reference_max': ref_max,
            'reference_text': ref_text,
            'flag': flag_value,
            'sample_date': sample_date,
            'result_date': result_date,
            'doctor': doctor_value,
            'row_number': row_idx
        }
    
    def _parse_result_value(self, value: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
        """Парсит значение результата"""
        if not value:
            return None, None
        
        value_str = str(value).strip()
        
        # Текстовые значения
        text_mapping = {
            'не обнаружено': 'Не обнаружено',
            'отрицательный': 'Отрицательный',
            'положительный': 'Положительный',
            'норма': 'Норма',
            'отр': 'Отрицательный',
            'пол': 'Положительный',
            'обнаружено': 'Обнаружено',
            'полож': 'Положительный'
        }
        
        for key, normalized in text_mapping.items():
            if key in value_str.lower():
                return None, normalized
        
        # Пробуем извлечь число
        try:
            # Очищаем строку
            clean_str = re.sub(r'[^\d\.,\-+\s]', ' ', value_str)
            clean_str = clean_str.replace(',', '.')
            
            # Ищем числа
            numbers = re.findall(r'[-+]?\d*\.?\d+', clean_str)
            
            if numbers:
                # Если диапазон (например, "8-12")
                if '-' in value_str or '—' in value_str or '–' in value_str:
                    if len(numbers) >= 2:
                        num1 = float(numbers[0])
                        num2 = float(numbers[1])
                        # Возвращаем среднее и текстовое представление
                        return (num1 + num2) / 2, f"{num1}-{num2}"
                
                # Одно число
                return float(numbers[0]), None
        except:
            pass
        
        # Если не число, возвращаем как текст
        return None, value_str
    
    def _parse_reference_range(self, ref_str: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """Парсит референсный диапазон"""
        if not ref_str:
            return None, None, str(ref_str)
        
        ref_str = str(ref_str)
        clean_str = re.sub(r'[^\d\.,\-—–\s]', ' ', ref_str)
        clean_str = clean_str.replace(',', '.')
        
        try:
            numbers = re.findall(r'\d+\.?\d*', clean_str)
            
            if len(numbers) >= 2:
                return float(numbers[0]), float(numbers[1]), ref_str
            elif len(numbers) == 1:
                num = float(numbers[0])
                return num, num, ref_str
        except:
            pass
        
        return None, None, ref_str
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Парсит дату"""
        if not date_str:
            return None
        
        date_str = str(date_str).strip()
        
        # Форматы дат
        date_formats = [
            "%d.%m.%Y",   # 18.12.2023
            "%d/%m/%Y",   # 18/12/2023
            "%Y-%m-%d",   # 2023-12-18
            "%d.%m.%y",   # 18.12.23
            "%d/%m/%y",   # 18/12/23
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _create_test_from_data(self, test_data: Dict, sheet_name: str) -> Optional[LabTest]:
        """Создает объект LabTest из данных"""
        try:
            # Определяем категорию по названию теста
            category = self._determine_test_category(
                test_data['original_name'],
                test_data.get('category')
            )
        
            # Создаем объект LabTest
            test = LabTest(
                name=test_data['original_name'],  # Позже нормализуем
                original_name=test_data['original_name'],
                value=test_data.get('value'),
                numeric_value=test_data.get('numeric_value'),
                text_value=test_data.get('text_value'),
                original_value=test_data.get('value'),  # Сохраняем оригинальное значение
                unit=test_data.get('unit'),
                reference_min=test_data.get('reference_min'),
                reference_max=test_data.get('reference_max'),
                reference_text=test_data.get('reference_text'),
                flag=test_data.get('flag'),
                category=category,
                subcategory=test_data.get('subcategory'),
                sample_date=test_data.get('sample_date'),
                result_date=test_data.get('result_date'),
                doctor=test_data.get('doctor'),
                sheet_name=sheet_name,
                row_number=test_data.get('row_number')
            )
        
            return test
        
        except Exception as e:
            logger.error(f"Ошибка при создании теста {test_data.get('original_name', 'unknown')}: {e}")
            return None
    
    def _determine_test_category(self, test_name: str, current_category: Optional[TestCategory]) -> TestCategory:
        """Определяет категорию теста по его названию"""
        test_name_lower = test_name.lower()
        
        # Если уже определена категория, используем ее
        if current_category:
            return current_category
        
        # Ищем по ключевым словам
        for category, keywords in self.TEST_CATEGORIES.items():
            if any(keyword in test_name_lower for keyword in keywords):
                return category
        
        return TestCategory.OTHER