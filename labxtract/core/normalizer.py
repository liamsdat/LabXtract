"""
Нормализатор данных лабораторных анализов
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import LabTest, TestCategory


class DataNormalizer:
    """Нормализует названия тестов, единицы измерения и значения"""
    
    # Словарь нормализации названий тестов
    TEST_NAME_MAPPING = {
        # Гематология
        'гемоглобин(hgb)': 'Гемоглобин',
        'гемоглобин': 'Гемоглобин',
        'hgb': 'Гемоглобин',
        'hemoglobin': 'Гемоглобин',
        
        'лейкоциты(wbc)': 'Лейкоциты',
        'лейкоциты': 'Лейкоциты',
        'wbc': 'Лейкоциты',
        'white blood cells': 'Лейкоциты',
        
        'эритроциты(rbc)': 'Эритроциты',
        'эритроциты': 'Эритроциты',
        'rbc': 'Эритроциты',
        'red blood cells': 'Эритроциты',
        
        'тромбоциты(plt)': 'Тромбоциты',
        'тромбоциты': 'Тромбоциты',
        'plt': 'Тромбоциты',
        'platelets': 'Тромбоциты',
        
        'гематокрит(hct)': 'Гематокрит',
        'гематокрит': 'Гематокрит',
        'hct': 'Гематокрит',
        
        'соэ': 'СОЭ',
        'соэ по панченкову': 'СОЭ',
        'esr': 'СОЭ',
        
        # Биохимия
        'глюкоза': 'Глюкоза',
        'глюкоза в крови': 'Глюкоза',
        'glucose': 'Глюкоза',
        
        'креатинин': 'Креатинин',
        'creatinine': 'Креатинин',
        
        'мочевина': 'Мочевина',
        'urea': 'Мочевина',
        
        'холестерин': 'Холестерин общий',
        'холестерин общий': 'Холестерин общий',
        'cholesterol': 'Холестерин общий',
        
        'алт': 'АЛТ',
        'аланинаминотрансфераза': 'АЛТ',
        'alt': 'АЛТ',
        
        'аст': 'АСТ',
        'аспартатаминотрансфераза': 'АСТ',
        'ast': 'АСТ',
        
        'билирубин общий': 'Билирубин общий',
        'общий билирубин': 'Билирубин общий',
        'total bilirubin': 'Билирубин общий',
        
        'билирубин прямой': 'Билирубин прямой',
        'прямой билирубин': 'Билирубин прямой',
        'direct bilirubin': 'Билирубин прямой',
        
        'общий белок': 'Общий белок',
        'total protein': 'Общий белок',
        
        'альбумин': 'Альбумин',
        'albumin': 'Альбумин',
        
        # Гормоны
        'ттг': 'ТТГ',
        'тиреотропный гормон': 'ТТГ',
        'tsh': 'ТТГ',
        'thyroid stimulating hormone': 'ТТГ',
        
        'т4 свободный': 'Т4 свободный',
        'свободный т4': 'Т4 свободный',
        'free t4': 'Т4 свободный',
        
        'т3 свободный': 'Т3 свободный',
        'свободный т3': 'Т3 свободный',
        'free t3': 'Т3 свободный',
        
        # Гликированный гемоглобин
        'hba1c': 'HbA1c',
        'гликированный гемоглобин': 'HbA1c',
        'гемоглобин a1c': 'HbA1c',
        'glycated hemoglobin': 'HbA1c',
        
        # Моча
        'белок в моче': 'Белок в моче',
        'протеинурия': 'Белок в моче',
        'protein urine': 'Белок в моче',
        
        'глюкоза в моче': 'Глюкоза в моче',
        'глюкозурия': 'Глюкоза в моче',
        'glucose urine': 'Глюкоза в моче',
        
        # Микробиология
        'трихомонады': 'Trichomonas vaginalis',
        'trichomonas': 'Trichomonas vaginalis',
        
        'кандида': 'Candida',
        'дрожжевые клетки': 'Candida',
        
        # Иммунология
        'вич': 'ВИЧ',
        'hiv': 'ВИЧ',
        'антитела к вич': 'ВИЧ',
        
        'гепатит в': 'Гепатит B',
        'hbsag': 'Гепатит B',
        'гепатит b': 'Гепатит B',
        
        'гепатит с': 'Гепатит C',
        'анти-hcv': 'Гепатит C',
        'гепатит c': 'Гепатит C',
        
        'сифилис': 'Сифилис',
        'рмп': 'Сифилис',
        'syphilis': 'Сифилис',
    }
    
    # Нормализация единиц измерения
    UNIT_NORMALIZATION = {
        'г/л': 'г/л',
        'г/л.': 'г/л',
        'г/л,': 'г/л',
        'гл': 'г/л',
        
        'ммоль/л': 'ммоль/л',
        'ммольл': 'ммоль/л',
        'ммоль': 'ммоль/л',
        
        'мкмоль/л': 'мкмоль/л',
        'мкмоль': 'мкмоль/л',
        
        '%': '%',
        'процент': '%',
        'percent': '%',
        
        '10*9/л': '10⁹/л',
        '10^9/л': '10⁹/л',
        '10e9/л': '10⁹/л',
        '10^9л': '10⁹/л',
        
        '10*12/л': '10¹²/л',
        '10^12/л': '10¹²/л',
        '10e12/л': '10¹²/л',
        '10^12л': '10¹²/л',
        
        'ед/л': 'Ед/л',
        'е/л': 'Ед/л',
        'u/l': 'Ед/л',
        
        'мке/мл': 'мкЕд/мл',
        'мкме/мл': 'мкЕд/мл',
        'mu/l': 'мкЕд/мл',
        
        'нг/мл': 'нг/мл',
        'ng/ml': 'нг/мл',
        
        'пг': 'пг',
        'pg': 'пг',
        
        'фл': 'фл',
        'fl': 'фл',
        'фемтолитр': 'фл',
        
        'мг/дл': 'мг/дл',
        'mg/dl': 'мг/дл',
        
        'г/дл': 'г/дл',
        'g/dl': 'г/дл',
        
        'мл/ч': 'мм/ч',
        'mm/h': 'мм/ч',
        'миллиметрвчас': 'мм/ч',
        
        'безразмернаяединица': 'б/р',
        'безразмерная': 'б/р',
        'б/р': 'б/р',
    }
    
    def normalize_test(self, test: LabTest) -> LabTest:
        """Нормализует один тест"""
        if not test or not test.name:
            return test
    
        # Нормализуем название
        normalized_name = self._normalize_test_name(test.original_name)
        test.name = normalized_name
    
        # Нормализуем единицы измерения
        if test.unit:
            test.unit = self._normalize_unit(test.unit)
    
        # Нормализуем текстовые значения
        if test.text_value:
            test.text_value = self._normalize_text_value(test.text_value)
    
        # Нормализуем флаг
        if test.flag:
            test.flag = self._normalize_flag(test.flag)
    
        # Обновляем категорию на основе нормализованного имени
        test._determine_category()
    
        return test
    
    def normalize_report(self, report) -> None:
        """Нормализует все тесты в отчете"""
        for i, test in enumerate(report.tests):
            report.tests[i] = self.normalize_test(test)
    
    def _normalize_test_name(self, name: str) -> str:
        """Нормализует название теста"""
        if not name:
            return name
        
        # Очищаем название
        clean_name = self._clean_string(name)
        
        # Ищем в маппинге
        for key, normalized in self.TEST_NAME_MAPPING.items():
            if key.lower() in clean_name.lower():
                return normalized
        
        # Если не нашли, капитализируем и убираем лишнее
        return self._capitalize_name(clean_name)
    
    def _clean_string(self, text: str) -> str:
        """Очищает строку от лишних символов"""
        if not text:
            return text
        
        # Удаляем лишние пробелы
        text = ' '.join(text.split())
        
        # Удаляем ненужные символы в начале и конце
        text = text.strip(' :;,-.')
        
        # Заменяем множественные пробелы на один
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _capitalize_name(self, name: str) -> str:
        """Капитализирует название с учетом медицинских аббревиатур"""
        # Разбиваем на слова
        words = name.split()
        
        # Капитализируем каждое слово, но с учетом аббревиатур
        capitalized_words = []
        for word in words:
            # Если это аббревиатура (все буквы заглавные или смесь букв и цифр)
            if re.match(r'^[A-ZА-Я0-9]+$', word.upper()):
                capitalized_words.append(word.upper())
            else:
                capitalized_words.append(word.capitalize())
        
        result = ' '.join(capitalized_words)
        
        # Специальные замены для медицинских аббревиатур
        replacements = [
            (r'\bAlt\b', 'АЛТ'),
            (r'\bAst\b', 'АСТ'),
            (r'\bTsh\b', 'ТТГ'),
            (r'\bHba1c\b', 'HbA1c'),
            (r'\bHba\b', 'HbA'),
            (r'\bHgb\b', 'HGB'),
            (r'\bWbc\b', 'WBC'),
            (r'\bRbc\b', 'RBC'),
            (r'\bPlt\b', 'PLT'),
            (r'\bHct\b', 'HCT'),
        ]
        
        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _normalize_unit(self, unit: str) -> str:
        """Нормализует единицы измерения"""
        if not unit:
            return unit
        
        # Очищаем строку
        clean_unit = str(unit).lower().strip()
        clean_unit = re.sub(r'[^\w/]', '', clean_unit)
        
        # Ищем в маппинге
        for key, normalized in self.UNIT_NORMALIZATION.items():
            if key.lower() in clean_unit.lower():
                return normalized
        
        # Если не нашли, возвращаем оригинал с небольшой очисткой
        return unit.strip()
    
    def _normalize_text_value(self, text: str) -> str:
        """Нормализует текстовое значение"""
        if not text:
            return text
        
        text_lower = text.lower().strip()
        
        # Маппинг текстовых значений
        mapping = {
            'не обнаружено': 'Не обнаружено',
            'не обнар': 'Не обнаружено',
            'отрицательный': 'Отрицательный',
            'отрицат': 'Отрицательный',
            'отр': 'Отрицательный',
            'положительный': 'Положительный',
            'положит': 'Положительный',
            'пол': 'Положительный',
            'норма': 'Норма',
            'норм': 'Норма',
            'повышен': 'Повышен',
            'повыш': 'Повышен',
            'понижен': 'Понижен',
            'пониж': 'Понижен',
            'сомнительный': 'Сомнительный',
            'сомнит': 'Сомнительный',
            'единично': 'Единично',
            'един': 'Единично',
            'ед': 'Единично',
            'сплошь': 'Сплошь',
            'большое количество': 'Большое количество',
            'скопление': 'Скопление',
            'умеренное': 'Умеренное',
            'обильное': 'Обильное',
            'скудно': 'Скудно',
        }
        
        for key, value in mapping.items():
            if key in text_lower:
                return value
        
        return text
    
    def _normalize_flag(self, flag: str) -> str:
        """Нормализует флаг"""
        flag_lower = flag.lower().strip()
        
        mapping = {
            'норма': 'Норма',
            'normal': 'Норма',
            'повышен': 'Повышен',
            'high': 'Повышен',
            'понижен': 'Понижен',
            'low': 'Понижен',
            'сомнительный': 'Сомнительный',
            'abnormal': 'Сомнительный',
            'положительный': 'Положительный',
            'positive': 'Положительный',
            'отрицательный': 'Отрицательный',
            'negative': 'Отрицательный',
        }
        
        for key, value in mapping.items():
            if key in flag_lower:
                return value
        
        return flag