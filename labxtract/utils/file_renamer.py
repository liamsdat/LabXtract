#!/usr/bin/env python3
"""
Утилита для переименования Excel файлов в формат для LabXtract
Формат: "Фамилия Имя Отчество ДД.ММ.ГГГГ.xlsx"
"""

import os
import re
from pathlib import Path
from datetime import datetime
import pandas as pd
import click

@click.command()
@click.argument('input_dir', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='./renamed')
@click.option('--pattern', '-p', 
              default='{last_name} {first_name} {birth_date}.xlsx',
              help='Шаблон имени: {last_name}, {first_name}, {middle_name}, {birth_date}')
def rename_files(input_dir, output_dir, pattern):
    """
    Переименовывает Excel файлы для совместимости с LabXtract
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    excel_files = list(input_path.glob('*.xlsx')) + list(input_path.glob('*.xls'))
    
    if not excel_files:
        click.echo("❌ Не найдено Excel файлов")
        return
    
    click.echo(f"🔍 Найдено файлов: {len(excel_files)}")
    
    renamed_count = 0
    for file_path in excel_files:
        try:
            # Пробуем извлечь данные из файла
            patient_info = extract_patient_info(file_path)
            
            if patient_info:
                # Формируем новое имя
                new_name = create_filename(patient_info, pattern)
                new_path = output_path / new_name
                
                # Копируем файл
                import shutil
                shutil.copy2(file_path, new_path)
                
                click.echo(f"✅ {file_path.name} -> {new_name}")
                renamed_count += 1
            else:
                click.echo(f"⚠️  Не удалось извлечь данные из {file_path.name}")
                
        except Exception as e:
            click.echo(f"❌ Ошибка при обработке {file_path.name}: {e}")
    
    click.echo(f"\n📊 Итого переименовано: {renamed_count}/{len(excel_files)}")

def extract_patient_info(file_path: Path) -> dict:
    """Извлекает информацию о пациенте из Excel файла"""
    info = {}
    
    try:
        # Читаем все листы
        excel_file = pd.ExcelFile(file_path)
        
        # Ищем данные пациента в первых листах
        for sheet_name in excel_file.sheet_names[:3]:  # Проверяем первые 3 листа
            df = excel_file.parse(sheet_name, nrows=10, header=None)
            
            # Ищем ФИО в первых строках
            for i in range(min(5, len(df))):
                row_text = ' '.join(str(cell) for cell in df.iloc[i].dropna())
                
                # Паттерны для поиска ФИО
                patterns = [
                    # Пациент: Иванов Иван Иванович
                    r'пациент[:\s]+([А-Я][а-я]+)\s+([А-Я][а-я]+)\s+([А-Я][а-я]+)',
                    # ФИО: Иванов И.И.
                    r'фио[:\s]+([А-Я][а-я]+)\s+([А-Я])\.\s*([А-Я])\.',
                    # Иванов Иван
                    r'^([А-Я][а-я]+)\s+([А-Я][а-я]+)$',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, row_text, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        if len(groups) >= 2:
                            info['last_name'] = groups[0]
                            info['first_name'] = groups[1]
                            if len(groups) >= 3:
                                info['middle_name'] = groups[2]
                        
                        # Ищем дату рождения
                        date_patterns = [
                            r'(\d{2}\.\d{2}\.\d{4})',
                            r'(\d{2}/\d{2}/\d{4})',
                            r'(\d{4}-\d{2}-\d{2})',
                        ]
                        
                        for date_pattern in date_patterns:
                            date_match = re.search(date_pattern, row_text)
                            if date_match:
                                try:
                                    date_str = date_match.group(1)
                                    # Пробуем разные форматы
                                    for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
                                        try:
                                            info['birth_date'] = datetime.strptime(date_str, fmt)
                                            break
                                        except:
                                            continue
                                except:
                                    pass
                        
                        if info:
                            return info
    
    except Exception:
        pass
    
    # Если не нашли в содержимом, используем имя файла
    stem = file_path.stem
    name_match = re.match(r'^([А-Я][а-я]+)_?([А-Я][а-я]+)', stem)
    if name_match:
        info['last_name'] = name_match.group(1)
        info['first_name'] = name_match.group(2)
    
    return info

def create_filename(patient_info: dict, pattern: str) -> str:
    """Создает имя файла по шаблону"""
    # Заполняем шаблон
    result = pattern
    
    # Заменяем плейсхолдеры
    for key, value in patient_info.items():
        if key == 'birth_date' and isinstance(value, datetime):
            placeholder = '{birth_date}'
            replacement = value.strftime('%d.%m.%Y')
        elif key == 'middle_name' and value:
            # Для отчества можно использовать инициал
            placeholder = '{middle_name}'
            replacement = value
            # Альтернатива: только первая буква
            result = result.replace('{middle_name[0]}', value[0] if value else '')
        else:
            placeholder = f'{{{key}}}'
            replacement = str(value) if value else ''
        
        result = result.replace(placeholder, replacement)
    
    # Очищаем оставшиеся плейсхолдеры
    result = re.sub(r'\{[^}]+\}', '', result)
    
    # Очищаем двойные пробелы и добавляем расширение
    result = ' '.join(result.split()) + '.xlsx'
    
    return result

if __name__ == '__main__':
    rename_files()