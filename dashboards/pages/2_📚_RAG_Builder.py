from pathlib import Path
import sys
import runpy

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT.parent))

TARGET = ROOT / "dashboard_02_rag_builder.py"
runpy.run_path(str(TARGET))
