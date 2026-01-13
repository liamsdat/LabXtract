"""
CLI интерфейс для LabXtract
"""

import click
import sys
from pathlib import Path
import json
import logging
from datetime import datetime

# Используем абсолютные импорты
from labxtract.core.extractor import LabXtractEngine
from labxtract.core.models import PatientInfo  # ✅ ДОБАВЛЯЕМ ЭТОТ ИМПОРТ

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('labxtract.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """LabXtract - Интеллектуальный парсер лабораторных анализов из Excel"""
    pass


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output', '-o', default='./labxtract_output')
@click.option('--format', '-f', default='csv')
@click.option('--config', '-c', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True)
@click.option('--patient-source', '-ps', 
              type=click.Choice(['filename', 'sheet_name', 'auto']),
              default='auto',
              help='Источник данных о пациенте')
def parse(input_path, output, format, config, verbose, patient_source):
    """
    Парсинг Excel файлов с лабораторными анализами
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # === Создаем конфиг с настройкой источника данных ===
    if config:
        with open(config, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
        # Добавляем или обновляем настройку источника данных
        if 'data_source' not in user_config:
            user_config['data_source'] = {}
        user_config['data_source']['patient_info_source'] = patient_source
        
        # Сохраняем временный конфиг
        temp_config = Path('temp_config.json')
        with open(temp_config, 'w', encoding='utf-8') as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)
        config_path = temp_config
        is_temp_config = True
    else:
        # Создаем минимальный конфиг с настройкой источника
        temp_config = Path('temp_config.json')
        with open(temp_config, 'w', encoding='utf-8') as f:
            json.dump({
                'data_source': {
                    'patient_info_source': patient_source
                }
            }, f, ensure_ascii=False, indent=2)
        config_path = temp_config
        is_temp_config = True
    
    logger.info(f"Запуск парсинга: {input_path}")
    logger.info(f"Источник данных пациента: {patient_source}")
    
    # Создаем движок с конфигом (включая настройку источника данных)
    engine = LabXtractEngine(config_path)
    
    input_path = Path(input_path)
    output_dir = Path(output)
    
    # Определяем, что обрабатываем
    if input_path.is_file():
        logger.info(f"Обработка файла: {input_path.name}")
        reports = engine.process_file(input_path)
    else:
        logger.info(f"Обработка директории: {input_path}")
        reports = engine.process_directory(input_path)
    
    # Удаляем временный конфиг если создавали
    if 'is_temp_config' in locals() and is_temp_config and temp_config.exists():
        temp_config.unlink()
    
    if not reports:
        logger.error("Не удалось извлечь данные из файлов")
        sys.exit(1)
    
    logger.info(f"Успешно извлечено отчетов: {len(reports)}")
    
    # Создаем директорию для результатов
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Экспортируем в выбранный формат
    success = False
    
    if format in ['csv', 'all']:
        csv_path = output_dir / f"labxtract_results_{timestamp}.csv"
        if engine.export_to_csv(reports, csv_path):
            success = True
            click.echo(f"✅ CSV: {csv_path}")
    
    if format in ['json', 'all']:
        json_path = output_dir / f"labxtract_results_{timestamp}.json"
        if engine.export_to_json(reports, json_path):
            success = True
            click.echo(f"✅ JSON: {json_path}")
    
    if format in ['excel', 'all']:
        excel_path = output_dir / f"labxtract_results_{timestamp}.xlsx"
        if engine.export_to_excel(reports, excel_path):
            success = True
            click.echo(f"✅ Excel: {excel_path}")
    
    # Сводная информация
    total_tests = sum(len(report.tests) for report in reports)
    total_patients = len(set(
        report.patient.full_name or f"unknown_{i}" 
        for i, report in enumerate(reports)
    ))
    
    # Статистика по источникам данных
    source_stats = {}
    for report in reports:
        source = "unknown"
        if report.patient.full_name:
            # Проверяем, откуда взялись данные
            test_patient = PatientInfo()
            if test_patient.from_filename(report.source_file):
                if test_patient.full_name == report.patient.full_name:
                    source = "filename"
            elif test_patient.from_sheet_name(report.sheet_name):
                if test_patient.full_name == report.patient.full_name:
                    source = "sheet_name"
            else:
                source = "manual"  # Введены вручную или другой источник
        
        source_stats[source] = source_stats.get(source, 0) + 1
    
    click.echo(f"\n📊 Сводка:")
    click.echo(f"  Обработано файлов: {1 if input_path.is_file() else 'несколько'}")
    click.echo(f"  Найдено отчетов: {len(reports)}")
    click.echo(f"  Уникальных пациентов: {total_patients}")
    click.echo(f"  Всего тестов: {total_tests}")
    click.echo(f"  Аномальных тестов: {sum(report.abnormal_tests for report in reports)}")
    click.echo(f"  Источник данных пациента: {patient_source}")
    
    if source_stats:
        click.echo(f"  Распределение источников:")
        for source, count in source_stats.items():
            click.echo(f"    - {source}: {count} отчетов")
    
    click.echo(f"  Результаты сохранены в: {output_dir}")
    
    if success:
        click.echo(f"\n✅ Парсинг завершен успешно!")
    else:
        click.echo(f"\n❌ Парсинг завершен с ошибками")
        sys.exit(1)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--sheet', '-s', default=None,
              help='Название листа для анализа (если не указано - первый)')
def analyze(file_path, sheet):
    """
    Анализ структуры Excel файла без парсинга
    """
    import pandas as pd
    
    file_path = Path(file_path)
    click.echo(f"🔍 Анализ файла: {file_path.name}")
    
    try:
        # Читаем Excel файл
        excel_file = pd.ExcelFile(file_path)
        
        click.echo(f"📄 Листы в файле ({len(excel_file.sheet_names)}):")
        for i, sheet_name in enumerate(excel_file.sheet_names, 1):
            click.echo(f"  {i}. {sheet_name}")
        
        # Анализируем указанный или первый лист
        sheet_to_analyze = sheet or excel_file.sheet_names[0]
        click.echo(f"\n📊 Анализ листа: {sheet_to_analyze}")
        
        df = excel_file.parse(sheet_to_analyze, header=None, dtype=str)
        click.echo(f"  Размер: {df.shape[0]} строк, {df.shape[1]} столбцов")
        
        # Показываем первые строки
        click.echo(f"\n  Первые 5 строк:")
        for i in range(min(5, len(df))):
            row_preview = []
            for j in range(min(5, len(df.columns))):
                cell = df.iat[i, j]
                preview = str(cell)[:20] + '...' if len(str(cell)) > 20 else str(cell)
                row_preview.append(preview)
            click.echo(f"    {i}: {' | '.join(row_preview)}")
        
        # Ищем возможные таблицы
        click.echo(f"\n🔎 Поиск таблиц с анализами:")
        
        # Ищем строки с ключевыми словами
        keywords = ['показатель', 'анализ', 'результат', 'норма', 'ед.']
        
        for i in range(min(20, len(df))):
            row_text = ' '.join(str(cell).lower() for cell in df.iloc[i].dropna())
            
            found_keywords = [kw for kw in keywords if kw in row_text]
            if found_keywords:
                click.echo(f"  Строка {i+1}: найдены ключевые слова - {', '.join(found_keywords)}")
                
                # Показываем содержимое строки
                row_preview = ' | '.join(str(cell)[:15] for cell in df.iloc[i].dropna()[:5])
                click.echo(f"       Содержимое: {row_preview}...")
        
        # Парсим информацию о пациенте из названия листа
        patient = PatientInfo()
        if patient.from_sheet_name(sheet_to_analyze):
            click.echo(f"\n👤 Информация о пациенте из названия листа:")
            click.echo(f"  ФИО: {patient.full_name}")
            click.echo(f"  Фамилия: {patient.last_name}")
            click.echo(f"  Имя: {patient.first_name}")
            if patient.middle_name:
                click.echo(f"  Отчество: {patient.middle_name}")
            if patient.birth_date:
                click.echo(f"  Дата рождения: {patient.birth_date.strftime('%d.%m.%Y')}")
            if patient.age:
                click.echo(f"  Возраст: {patient.age}")
        
        # Также пробуем из имени файла
        patient_from_file = PatientInfo()
        if patient_from_file.from_filename(file_path.name):
            click.echo(f"\n👤 Информация о пациенте из имени файла:")
            click.echo(f"  ФИО: {patient_from_file.full_name}")
            if patient_from_file.birth_date:
                click.echo(f"  Дата рождения: {patient_from_file.birth_date.strftime('%d.%m.%Y')}")
            if patient_from_file.age:
                click.echo(f"  Возраст: {patient_from_file.age}")
        
    except Exception as e:
        click.echo(f"❌ Ошибка при анализе файла: {e}")
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path())
@click.option('--overwrite', '-o', is_flag=True,
              help='Перезаписать существующий файл')
def create_config(config_file, overwrite):
    """
    Создает файл конфигурации с настройками по умолчанию
    """
    config_path = Path(config_file)
    
    if config_path.exists() and not overwrite:
        click.echo(f"❌ Файл {config_file} уже существует. Используйте --overwrite для перезаписи.")
        sys.exit(1)
    
    default_config = {
        "data_source": {
            "patient_info_source": "auto"
        },
        "parser": {
            "keywords": {
                "test_name": ["показатель", "анализ", "название", "test"],
                "result": ["результат", "значение", "value", "уровень"],
                "unit": ["ед.изм", "единиц", "unit", "измерен"],
                "reference": ["норма", "референс", "reference", "диапазон"],
                "flag": ["флаг", "flag", "статус"],
                "date_sample": ["дата взятия", "дата исслед", "sample date"],
                "date_result": ["дата выполн", "дата результата", "result date"],
                "doctor": ["врач", "doctor", "исполнитель"]
            },
            "max_rows_to_check": 20,
            "date_formats": ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y"]
        },
        "normalizer": {
            "strict_mode": False,
            "custom_mappings": {
                "test_names": {},
                "units": {}
            }
        },
        "output": {
            "encoding": "utf-8-sig",
            "separator": ",",
            "date_format": "%d.%m.%Y",
            "create_summary": True
        }
    }
    
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        
        click.echo(f"✅ Файл конфигурации создан: {config_path}")
        click.echo(f"📋 Настройки по умолчанию:")
        click.echo(f"  • Источник данных пациента: {default_config['data_source']['patient_info_source']}")
        click.echo(f"  • Ключевые слова для парсера: {len(default_config['parser']['keywords'])} категорий")
        click.echo(f"  • Формат вывода: CSV, JSON, Excel")
        click.echo("\nВы можете отредактировать этот файл для настройки парсера.")
        
    except Exception as e:
        click.echo(f"❌ Ошибка при создании конфигурации: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()