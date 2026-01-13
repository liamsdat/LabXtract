"""
Основной движок LabXtract
"""

import pandas as pd
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from .models import LabReport, PatientInfo
from ..parsers.excel_parser import ExcelLabParser
from .normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class LabXtractEngine:
    """Основной движок для обработки лабораторных отчетов"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Инициализирует движок
        
        Args:
            config_path: Путь к файлу конфигурации (опционально)
        """
        self.config = self._load_config(config_path)
        self.parser = ExcelLabParser(self.config.get('parser', {}))
        self.normalizer = DataNormalizer()
        
        logger.info("LabXtractEngine инициализирован")
    
    def process_file(self, file_path: Path) -> List[LabReport]:
        """
        Обрабатывает один файл с лабораторными отчетами
        
        Args:
            file_path: Путь к Excel файлу
            
        Returns:
            Список отчетов (по одному на каждый лист)
        """
        logger.info(f"Начинаю обработку файла: {file_path}")
        
        try:
            # 1. Определяем источник данных из конфига
            patient_source = self.config.get('data_source', {}).get('patient_info_source', 'auto')
            
            # 2. Парсим файл
            raw_reports = self.parser.parse_file(file_path)
            
            if not raw_reports:
                logger.warning(f"Не удалось извлечь данные из файла: {file_path}")
                return []
            
            # 3. Обновляем информацию о пациенте в зависимости от источника
            if patient_source != 'auto':
                self._update_patient_source(raw_reports, file_path, patient_source)
            
            # 4. Нормализуем каждый отчет
            normalized_reports = []
            for report in raw_reports:
                self.normalizer.normalize_report(report)
                normalized_reports.append(report)
            
            logger.info(f"Файл обработан успешно. Отчетов: {len(normalized_reports)}")
            return normalized_reports
            
        except Exception as e:
            logger.error(f"Ошибка при обработке файла {file_path}: {e}")
            raise
    
    def _update_patient_source(self, reports: List[LabReport], file_path: Path, source: str):
        """Обновляет источник данных пациента в отчетах"""
        for report in reports:
            if source == 'filename':
                # Пробуем извлечь из имени файла
                patient_from_file = PatientInfo()
                if patient_from_file.from_filename(file_path.name):
                    if patient_from_file.full_name:
                        report.patient = patient_from_file
                        logger.debug(f"Обновлен пациент из имени файла: {patient_from_file.full_name}")
            # Для 'sheet_name' оставляем как есть (уже извлечено парсером)
    
    def process_directory(self, directory_path: Path) -> List[LabReport]:
        """
        Обрабатывает все Excel файлы в директории
        
        Args:
            directory_path: Путь к директории
            
        Returns:
            Список всех отчетов из всех файлов
        """
        logger.info(f"Обработка директории: {directory_path}")
        
        all_reports = []
        file_count = 0
        
        # Ищем Excel файлы
        for pattern in ['*.xlsx', '*.xls', '*.xlsm']:
            for file_path in directory_path.glob(pattern):
                try:
                    file_reports = self.process_file(file_path)
                    all_reports.extend(file_reports)
                    file_count += 1
                    logger.info(f"  Обработан: {file_path.name} ({len(file_reports)} отчетов)")
                except Exception as e:
                    logger.error(f"  Ошибка при обработке {file_path}: {e}")
        
        logger.info(f"Обработка директории завершена. Файлов: {file_count}, отчетов: {len(all_reports)}")
        return all_reports
    
    def export_to_csv(self, reports: List[LabReport], output_path: Path) -> bool:
        """
        Экспортирует отчеты в CSV файл
        
        Args:
            reports: Список отчетов
            output_path: Путь для сохранения CSV
            
        Returns:
            True если успешно, False в противном случае
        """
        if not reports:
            logger.warning("Нет отчетов для экспорта")
            return False
        
        try:
            # Собираем все данные в один DataFrame
            all_data = []
            
            for report in reports:
                df = report.to_dataframe()
                if not df.empty:
                    all_data.append(df)
            
            if not all_data:
                logger.warning("Нет данных для экспорта")
                return False
            
            # Объединяем все DataFrame
            combined_df = pd.concat(all_data, ignore_index=True)
            
            # Сохраняем в CSV
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Настройки экспорта
            encoding = self.config.get('output', {}).get('encoding', 'utf-8-sig')
            separator = self.config.get('output', {}).get('separator', ',')
            
            combined_df.to_csv(
                output_path,
                index=False,
                encoding=encoding,
                sep=separator
            )
            
            logger.info(f"Данные экспортированы в: {output_path}")
            logger.info(f"  Всего записей: {len(combined_df)}")
            logger.info(f"  Столбцов: {len(combined_df.columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте в CSV: {e}")
            return False
    
    def export_to_json(self, reports: List[LabReport], output_path: Path) -> bool:
        """
        Экспортирует отчеты в JSON файл
        
        Args:
            reports: Список отчетов
            output_path: Путь для сохранения JSON
            
        Returns:
            True если успешно, False в противном случае
        """
        if not reports:
            logger.warning("Нет отчетов для экспорта")
            return False
        
        try:
            # Конвертируем отчеты в словари
            reports_data = [report.to_dict() for report in reports]
            
            # Сохраняем в JSON
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(reports_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Данные экспортированы в: {output_path}")
            logger.info(f"  Отчетов: {len(reports)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте в JSON: {e}")
            return False
    
    def export_to_excel(self, reports: List[LabReport], output_path: Path) -> bool:
        """
        Экспортирует отчеты в Excel файл
        
        Args:
            reports: Список отчетов
            output_path: Путь для сохранения Excel
            
        Returns:
            True если успешно, False в противном случае
        """
        if not reports:
            logger.warning("Нет отчетов для экспорта")
            return False
        
        try:
            # Создаем Excel writer
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Сводная таблица по пациентам
                summary_data = []
                
                for report in reports:
                    summary_data.append({
                        'Пациент': report.patient.full_name or 'Неизвестно',
                        'Дата рождения': report.patient.birth_date.strftime('%d.%m.%Y') 
                                      if report.patient.birth_date else 'Неизвестно',
                        'Возраст': report.patient.age or 'Неизвестно',
                        'Файл': report.source_file or 'Неизвестно',
                        'Лист': report.sheet_name or 'Неизвестно',
                        'Всего тестов': report.total_tests,
                        'Аномальных тестов': report.abnormal_tests,
                        'Дата отчета': report.report_date.strftime('%d.%m.%Y') 
                                     if report.report_date else 'Неизвестно'
                    })
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='Сводка', index=False)
                
                # Данные тестов по каждому отчету
                for i, report in enumerate(reports):
                    sheet_name = f"Отчет_{i+1}"
                    if report.patient.full_name:
                        # Ограничиваем длину имени листа (Excel максимум 31 символ)
                        sheet_name = report.patient.full_name[:28] + '...' \
                                   if len(report.patient.full_name) > 31 \
                                   else report.patient.full_name
                    
                    df = report.to_dataframe()
                    if not df.empty:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            logger.info(f"Данные экспортированы в: {output_path}")
            logger.info(f"  Отчетов: {len(reports)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте в Excel: {e}")
            return False
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        default_config = {
            'data_source': {
                'patient_info_source': 'auto'
            },
            'parser': {
                'max_rows_to_check': 20,
                'date_formats': ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']
            },
            'normalizer': {
                'strict_mode': False
            },
            'output': {
                'encoding': 'utf-8-sig',
                'separator': ',',
                'date_format': '%d.%m.%Y'
            }
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Объединяем с дефолтными настройками
                import copy
                merged_config = copy.deepcopy(default_config)
                
                # Рекурсивное слияние словарей
                def merge_dicts(d1, d2):
                    for key, value in d2.items():
                        if key in d1 and isinstance(d1[key], dict) and isinstance(value, dict):
                            merge_dicts(d1[key], value)
                        else:
                            d1[key] = value
                
                merge_dicts(merged_config, user_config)
                return merged_config
                
            except Exception as e:
                logger.warning(f"Не удалось загрузить конфиг {config_path}: {e}. Использую настройки по умолчанию")
        
        return default_config