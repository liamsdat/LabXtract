# excel_lab_parser/conftest.py
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
