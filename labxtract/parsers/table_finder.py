"""
Поиск таблиц в Excel листе
Находит и извлекает таблицы с лабораторными данными
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Set
import logging
import re

logger = logging.getLogger(__name__)


class TableFinder:
    """Поиск таблиц с данными в Excel листе"""
    
    # Паттерны для поиска начала таблицы
    TABLE_START_PATTERNS = [
        # Заголовок таблицы с анализами
        r'.*показатель.*результат.*',
        r'.*название.*анализ.*значение.*',
        r'.*test.*name.*result.*value.*',
        r'.*parameter.*result.*unit.*',
    ]
    
    # Столбцы, которые должны быть в таблице с анализами
    REQUIRED_COLUMNS = {
        'test_name': ['показатель', 'анализ', 'название', 'test', 'parameter'],
        'result': ['результат', 'значение', 'value', 'result'],
        'unit': ['ед.', 'единиц', 'unit', 'измерен'],
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.found_tables = []
        
    def find_tables(self, df: pd.DataFrame) -> List[Dict]:
        """
        Находит все таблицы в DataFrame
        
        Args:
            df: DataFrame с данными листа
            
        Returns:
            Список найденных таблиц с метаданными
        """
        tables = []
        
        if df.empty:
            return tables
        
        logger.info(f"Поиск таблиц в DataFrame размером {df.shape}")
        
        # Ищем все потенциальные начала таблиц
        potential_starts = self._find_potential_table_starts(df)
        
        for start_row in potential_starts:
            table = self._extract_table_from_start(df, start_row)
            if table and self._is_valid_table(table['data']):
                tables.append(table)
                logger.debug(f"Найдена таблица в строках {table['start_row']}-{table['end_row']}")
        
        # Если не нашли таблицы стандартным способом, пробуем другие методы
        if not tables:
            tables = self._find_tables_alternative(df)
        
        # Фильтруем дубликаты и пересекающиеся таблицы
        tables = self._filter_overlapping_tables(tables)
        
        # Сортируем по начальной строке
        tables.sort(key=lambda x: x['start_row'])
        
        self.found_tables = tables
        logger.info(f"Найдено таблиц: {len(tables)}")
        
        return tables
    
    def _find_potential_table_starts(self, df: pd.DataFrame) -> List[int]:
        """Находит потенциальные начала таблиц"""
        starts = []
        
        # Проверяем первые 100 строк
        max_rows_to_check = min(100, len(df))
        
        for row_idx in range(max_rows_to_check):
            row = df.iloc[row_idx]
            row_text = self._row_to_text(row)
            
            # Проверяем паттерны начала таблицы
            for pattern in self.TABLE_START_PATTERNS:
                if re.match(pattern, row_text, re.IGNORECASE):
                    starts.append(row_idx)
                    break
            
            # Проверяем наличие необходимых столбцов
            if self._row_contains_required_columns(row):
                starts.append(row_idx)
        
        # Убираем дубликаты и сортируем
        starts = sorted(set(starts))
        
        # Фильтруем слишком близкие начала (разница < 3 строк)
        filtered_starts = []
        prev_start = -10  # Начальное значение
        
        for start in starts:
            if start - prev_start >= 3:
                filtered_starts.append(start)
                prev_start = start
        
        return filtered_starts
    
    def _row_to_text(self, row: pd.Series) -> str:
        """Преобразует строку DataFrame в текст"""
        return ' '.join(str(cell).lower() for cell in row.dropna())
    
    def _row_contains_required_columns(self, row: pd.Series) -> bool:
        """Проверяет, содержит ли строка необходимые столбцы таблицы"""
        row_text = self._row_to_text(row)
        
        # Проверяем наличие хотя бы одного столбца из каждой обязательной категории
        found_categories = set()
        
        for column_type, keywords in self.REQUIRED_COLUMNS.items():
            if any(keyword in row_text for keyword in keywords):
                found_categories.add(column_type)
        
        # Нужны минимум 2 из 3 обязательных категорий
        return len(found_categories) >= 2
    
    def _extract_table_from_start(self, df: pd.DataFrame, start_row: int) -> Optional[Dict]:
        """Извлекает таблицу, начиная с указанной строки"""
        if start_row >= len(df) - 1:
            return None
        
        # Определяем конец таблицы
        end_row = self._find_table_end(df, start_row)
        
        if end_row <= start_row:
            return None
        
        # Извлекаем данные таблицы
        table_data = df.iloc[start_row:end_row + 1].copy()
        
        # Определяем столбцы
        columns = self._identify_table_columns(table_data.iloc[0])
        
        # Определяем типы данных в столбцах
        column_types = self._analyze_column_types(table_data, columns)
        
        return {
            'start_row': start_row,
            'end_row': end_row,
            'data': table_data,
            'columns': columns,
            'column_types': column_types,
            'row_count': len(table_data),
            'column_count': len(columns),
            'header_row': 0,  # Относительно table_data
        }
    
    def _find_table_end(self, df: pd.DataFrame, start_row: int) -> int:
        """Находит конец таблицы, начиная с указанной строки"""
        if start_row >= len(df) - 1:
            return start_row
        
        # Ищем первую полностью пустую строку после начала таблицы
        for row_idx in range(start_row + 1, len(df)):
            row = df.iloc[row_idx]
            
            # Проверяем, пустая ли строка
            if self._is_empty_row(row):
                # Проверяем следующие строки, чтобы убедиться, что это конец таблицы
                lookahead = 2
                all_empty = True
                
                for i in range(1, min(lookahead + 1, len(df) - row_idx)):
                    if not self._is_empty_row(df.iloc[row_idx + i]):
                        all_empty = False
                        break
                
                if all_empty:
                    return row_idx - 1
        
        # Если не нашли пустую строку, возвращаем последнюю строку
        return len(df) - 1
    
    def _is_empty_row(self, row: pd.Series) -> bool:
        """Проверяет, пустая ли строка"""
        return all(pd.isna(cell) or str(cell).strip() == '' for cell in row)
    
    def _identify_table_columns(self, header_row: pd.Series) -> Dict[str, int]:
        """Определяет назначение столбцов таблицы"""
        columns = {}
        
        for col_idx, cell in enumerate(header_row):
            if pd.isna(cell):
                continue
            
            cell_text = str(cell).lower()
            
            # Определяем тип столбца
            column_type = self._determine_column_type(cell_text)
            if column_type:
                columns[column_type] = col_idx
        
        return columns
    
    def _determine_column_type(self, cell_text: str) -> Optional[str]:
        """Определяет тип столбца по тексту ячейки"""
        # Удаляем лишние пробелы и приводим к нижнему регистру
        text = cell_text.strip().lower()
        
        # Маппинг ключевых слов на типы столбцов
        column_mapping = {
            'test_name': ['показатель', 'анализ', 'название', 'test', 'parameter', 'name'],
            'result': ['результат', 'значение', 'value', 'result', 'level'],
            'unit': ['ед.', 'единиц', 'unit', 'измерен', 'measure', 'единицы'],
            'reference': ['норма', 'референс', 'reference', 'диапазон', 'range', 'нормы'],
            'flag': ['флаг', 'flag', 'статус', 'status', 'отклонение'],
            'date_sample': ['дата взятия', 'дата исследования', 'sample date', 'collection'],
            'date_result': ['дата выполнения', 'дата результата', 'result date'],
            'doctor': ['врач', 'doctor', 'исполнитель', 'executor', 'лаборант'],
            'notes': ['примечание', 'комментарий', 'notes', 'comment'],
        }
        
        for column_type, keywords in column_mapping.items():
            if any(keyword in text for keyword in keywords):
                return column_type
        
        return None
    
    def _analyze_column_types(self, table_data: pd.DataFrame, columns: Dict[str, int]) -> Dict[str, str]:
        """Анализирует типы данных в столбцах"""
        column_types = {}
        
        for column_name, col_idx in columns.items():
            if col_idx >= table_data.shape[1]:
                continue
            
            # Берем выборку данных из столбца (исключая заголовок)
            sample_data = []
            for i in range(1, min(10, len(table_data))):
                if col_idx < len(table_data.iloc[i]):
                    cell = table_data.iat[i, col_idx]
                    if not pd.isna(cell):
                        sample_data.append(str(cell))
            
            if not sample_data:
                column_types[column_name] = 'unknown'
                continue
            
            # Определяем тип данных
            data_type = self._determine_data_type(sample_data)
            column_types[column_name] = data_type
        
        return column_types
    
    def _determine_data_type(self, sample_data: List[str]) -> str:
        """Определяет тип данных по выборке"""
        if not sample_data:
            return 'empty'
        
        # Проверяем на числа
        numeric_count = 0
        for value in sample_data:
            try:
                # Пробуем преобразовать в число
                cleaned = str(value).replace(',', '.')
                if re.match(r'^[-+]?\d*\.?\d+$', cleaned):
                    numeric_count += 1
            except:
                pass
        
        if numeric_count / len(sample_data) > 0.7:
            return 'numeric'
        
        # Проверяем на даты
        date_patterns = [
            r'\d{2}\.\d{2}\.\d{4}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}',
        ]
        
        date_count = 0
        for value in sample_data:
            if any(re.search(pattern, str(value)) for pattern in date_patterns):
                date_count += 1
        
        if date_count / len(sample_data) > 0.5:
            return 'date'
        
        # Проверяем на текст (специальные медицинские значения)
        medical_texts = ['не обнаружено', 'отрицательный', 'положительный', 'норма', 'отр', 'пол']
        text_count = 0
        
        for value in sample_data:
            value_lower = str(value).lower()
            if any(medical_text in value_lower for medical_text in medical_texts):
                text_count += 1
        
        if text_count / len(sample_data) > 0.5:
            return 'medical_text'
        
        # По умолчанию - текст
        return 'text'
    
    def _is_valid_table(self, table_data: pd.DataFrame) -> bool:
        """Проверяет, является ли таблица валидной"""
        if table_data.empty or len(table_data) < 2:
            return False
        
        # Должна быть хотя бы одна строка данных (кроме заголовка)
        if len(table_data) < 3:  # Заголовок + минимум 1 строка данных
            return False
        
        # Проверяем, что есть хотя бы некоторые данные
        non_empty_cells = table_data.notna().sum().sum()
        if non_empty_cells < 5:  # Минимум 5 заполненных ячеек
            return False
        
        # Проверяем структуру (должны быть разные столбцы)
        if table_data.shape[1] < 2:
            return False
        
        return True
    
    def _find_tables_alternative(self, df: pd.DataFrame) -> List[Dict]:
        """Альтернативный метод поиска таблиц"""
        tables = []
        
        # Ищем большие блоки непустых данных
        current_start = None
        current_block_rows = 0
        
        for row_idx in range(len(df)):
            row = df.iloc[row_idx]
            
            if not self._is_empty_row(row):
                if current_start is None:
                    current_start = row_idx
                current_block_rows += 1
            else:
                if current_start is not None and current_block_rows >= 5:
                    # Проверяем, может ли этот блок быть таблицей
                    block_data = df.iloc[current_start:row_idx]
                    if self._block_could_be_table(block_data):
                        table = self._extract_table_from_start(df, current_start)
                        if table:
                            tables.append(table)
                
                current_start = None
                current_block_rows = 0
        
        # Проверяем последний блок
        if current_start is not None and current_block_rows >= 5:
            block_data = df.iloc[current_start:len(df)]
            if self._block_could_be_table(block_data):
                table = self._extract_table_from_start(df, current_start)
                if table:
                    tables.append(table)
        
        return tables
    
    def _block_could_be_table(self, block_data: pd.DataFrame) -> bool:
        """Проверяет, может ли блок данных быть таблицей"""
        if len(block_data) < 3:
            return False
        
        # Проверяем, есть ли строка, похожая на заголовок
        for i in range(min(3, len(block_data))):
            row = block_data.iloc[i]
            row_text = self._row_to_text(row)
            
            # Проверяем наличие ключевых слов таблицы
            table_keywords = ['показатель', 'результат', 'ед.', 'норма']
            found_keywords = sum(1 for kw in table_keywords if kw in row_text)
            
            if found_keywords >= 2:
                return True
        
        return False
    
    def _filter_overlapping_tables(self, tables: List[Dict]) -> List[Dict]:
        """Фильтрует пересекающиеся таблицы"""
        if not tables:
            return []
        
        # Сортируем по начальной строке
        tables.sort(key=lambda x: x['start_row'])
        
        filtered_tables = []
        current_end = -1
        
        for table in tables:
            if table['start_row'] > current_end:
                filtered_tables.append(table)
                current_end = table['end_row']
            else:
                # Таблицы пересекаются, выбираем лучшую
                prev_table = filtered_tables[-1]
                
                # Выбираем таблицу с большим количеством строк
                if table['row_count'] > prev_table['row_count']:
                    filtered_tables[-1] = table
                    current_end = table['end_row']
        
        return filtered_tables
    
    def get_table_statistics(self) -> Dict:
        """Возвращает статистику по найденным таблицам"""
        if not self.found_tables:
            return {'total_tables': 0}
        
        total_rows = sum(table['row_count'] for table in self.found_tables)
        total_columns = sum(table['column_count'] for table in self.found_tables)
        
        return {
            'total_tables': len(self.found_tables),
            'total_rows': total_rows,
            'total_columns': total_columns,
            'average_rows': total_rows / len(self.found_tables),
            'average_columns': total_columns / len(self.found_tables),
            'tables': [
                {
                    'start_row': table['start_row'],
                    'end_row': table['end_row'],
                    'rows': table['row_count'],
                    'columns': table['column_count'],
                    'column_types': table.get('column_types', {})
                }
                for table in self.found_tables
            ]
        }