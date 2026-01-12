"""
Детектор листов в Excel файле
Определяет, какие листы содержат лабораторные данные
"""

import pandas as pd
from typing import List, Dict, Optional, Set
import logging
import re

logger = logging.getLogger(__name__)


class SheetDetector:
    """Детектор листов с медицинскими данными"""
    
    # Ключевые слова, указывающие на медицинские данные
    MEDICAL_KEYWORDS = {
        'лабораторн': ['лабораторные', 'лаборатория', 'lab', 'laboratory'],
        'анализ': ['анализ', 'исследование', 'тест', 'study', 'test'],
        'медицинск': ['медицинск', 'медицинский', 'medical', 'clinic'],
        'пациент': ['пациент', 'больной', 'patient', 'client'],
        'результат': ['результат', 'значение', 'result', 'value'],
        'показатель': ['показатель', 'параметр', 'indicator', 'parameter'],
        'кровь': ['кровь', 'blood', 'гемо', 'гемато'],
        'моча': ['моча', 'urine', 'урин'],
        'биохими': ['биохими', 'биохимический', 'biochem'],
        'гормон': ['гормон', 'hormone', 'эндокрин'],
    }
    
    # Паттерны для определения, что лист содержит данные пациента
    PATIENT_PATTERNS = [
        # ФИО + дата рождения
        r'^[А-Я][а-я]+\s+[А-Я][а-я]+(?:\s+[А-Я][а-я]+)?\s+\d{2}\.\d{2}\.\d{4}$',
        # Фамилия И.О. + дата
        r'^[А-Я][а-я]+\s+[А-Я]\.\s*[А-Я]\.\s*\d{2}\.\d{2}\.\d{4}$',
        # Просто ФИО (без даты)
        r'^[А-Я][а-я]+\s+[А-Я][а-я]+\s+[А-Я][а-я]+$',
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._medical_sheets = set()
        self._non_medical_sheets = set()
        
    def detect_medical_sheets(self, excel_file: pd.ExcelFile) -> List[str]:
        """
        Определяет, какие листы содержат медицинские данные
        
        Args:
            excel_file: Объект ExcelFile
            
        Returns:
            Список названий листов с медицинскими данными
        """
        medical_sheets = []
        
        for sheet_name in excel_file.sheet_names:
            if self._is_medical_sheet(sheet_name, excel_file):
                medical_sheets.append(sheet_name)
                self._medical_sheets.add(sheet_name)
            else:
                self._non_medical_sheets.add(sheet_name)
        
        logger.info(f"Обнаружено медицинских листов: {len(medical_sheets)}/{len(excel_file.sheet_names)}")
        return medical_sheets
    
    def _is_medical_sheet(self, sheet_name: str, excel_file: pd.ExcelFile) -> bool:
        """Определяет, является ли лист медицинским"""
        # 1. Проверяем по названию листа
        if self._is_patient_sheet_by_name(sheet_name):
            return True
        
        # 2. Проверяем по содержимому (первые строки)
        try:
            df = excel_file.parse(sheet_name, nrows=10, header=None, dtype=str)
            
            # Проверяем наличие медицинских ключевых слов в первых строках
            if self._contains_medical_keywords(df):
                return True
            
            # Проверяем структуру таблицы (наличие заголовков)
            if self._has_table_structure(df):
                return True
                
        except Exception as e:
            logger.debug(f"Ошибка при анализе листа {sheet_name}: {e}")
        
        return False
    
    def _is_patient_sheet_by_name(self, sheet_name: str) -> bool:
        """Определяет по названию листа, содержит ли он данные пациента"""
        sheet_name = str(sheet_name).strip()
        
        # Проверяем паттерны с данными пациента
        for pattern in self.PATIENT_PATTERNS:
            if re.match(pattern, sheet_name, re.IGNORECASE):
                logger.debug(f"Лист '{sheet_name}' соответствует паттерну пациента")
                return True
        
        # Проверяем медицинские ключевые слова в названии
        sheet_lower = sheet_name.lower()
        
        # Список медицинских терминов в названиях листов
        medical_terms_in_name = [
            'анализ', 'лаборатор', 'медицин', 'пациент', 'карта',
            'история', 'результат', 'обследование', 'диагноз',
            'lab', 'medical', 'patient', 'results', 'report'
        ]
        
        if any(term in sheet_lower for term in medical_terms_in_name):
            return True
        
        return False
    
    def _contains_medical_keywords(self, df: pd.DataFrame) -> bool:
        """Проверяет, содержит ли DataFrame медицинские ключевые слова"""
        if df.empty:
            return False
        
        # Объединяем первые несколько строк в текст
        sample_text = ''
        for i in range(min(5, len(df))):
            row_text = ' '.join(str(cell).lower() for cell in df.iloc[i].dropna())
            sample_text += ' ' + row_text
        
        sample_text = sample_text.lower()
        
        # Проверяем наличие медицинских ключевых слов
        found_keywords = []
        
        for category, keywords in self.MEDICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in sample_text:
                    found_keywords.append(keyword)
        
        if found_keywords:
            logger.debug(f"Найдены медицинские ключевые слова: {found_keywords[:3]}")
            return True
        
        return False
    
    def _has_table_structure(self, df: pd.DataFrame) -> bool:
        """Проверяет, имеет ли DataFrame структуру таблицы с анализами"""
        if len(df) < 2:
            return False
        
        # Ищем строку с заголовками
        for i in range(min(5, len(df))):
            row = df.iloc[i]
            
            # Проверяем, содержит ли строка типичные заголовки
            header_keywords = ['показатель', 'анализ', 'результат', 'значение', 'норма', 'ед.']
            row_text = ' '.join(str(cell).lower() for cell in row.dropna())
            
            # Считаем количество совпадений с ключевыми словами заголовков
            matches = sum(1 for keyword in header_keywords if keyword in row_text)
            
            if matches >= 2:  # Если хотя бы 2 ключевых слова
                logger.debug(f"Найдена строка с заголовками в строке {i}")
                return True
        
        return False
    
    def get_sheet_statistics(self) -> Dict:
        """Возвращает статистику по обнаруженным листам"""
        return {
            'total_medical_sheets': len(self._medical_sheets),
            'total_non_medical_sheets': len(self._non_medical_sheets),
            'medical_sheets': list(self._medical_sheets),
            'non_medical_sheets': list(self._non_medical_sheets)
        }
    
    def classify_sheet_content(self, df: pd.DataFrame, sheet_name: str) -> Dict:
        """
        Классифицирует содержимое листа
        
        Returns:
            Словарь с классификацией
        """
        classification = {
            'sheet_name': sheet_name,
            'is_medical': False,
            'contains_patient_data': False,
            'contains_lab_data': False,
            'table_structure': False,
            'estimated_rows': len(df),
            'estimated_columns': len(df.columns) if not df.empty else 0,
            'keywords_found': [],
            'problems': []
        }
        
        # Проверяем по названию
        classification['contains_patient_data'] = self._is_patient_sheet_by_name(sheet_name)
        
        if df.empty:
            classification['problems'].append('Пустой DataFrame')
            return classification
        
        # Проверяем медицинские ключевые слова
        sample_text = ''
        for i in range(min(10, len(df))):
            row_text = ' '.join(str(cell).lower() for cell in df.iloc[i].dropna())
            sample_text += ' ' + row_text
        
        # Ищем ключевые слова
        found_keywords = []
        for category, keywords in self.MEDICAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in sample_text:
                    found_keywords.append(keyword)
        
        classification['keywords_found'] = found_keywords
        
        # Проверяем структуру таблицы
        classification['table_structure'] = self._has_table_structure(df)
        
        # Определяем, является ли лист медицинским
        classification['is_medical'] = (
            classification['contains_patient_data'] or 
            len(found_keywords) > 0 or 
            classification['table_structure']
        )
        
        # Определяем, содержит ли данные лабораторных анализов
        classification['contains_lab_data'] = (
            any(kw in ['анализ', 'лабораторн', 'результат', 'показатель'] for kw in found_keywords) or
            classification['table_structure']
        )
        
        # Проверяем проблемы
        if classification['estimated_rows'] < 3:
            classification['problems'].append('Слишком мало строк')
        
        if classification['estimated_columns'] < 3:
            classification['problems'].append('Слишком мало столбцов')
        
        # Проверяем наличие данных
        non_empty_cells = df.notna().sum().sum()
        total_cells = df.size
        if total_cells > 0 and non_empty_cells / total_cells < 0.1:
            classification['problems'].append('Менее 10% заполненных ячеек')
        
        return classification