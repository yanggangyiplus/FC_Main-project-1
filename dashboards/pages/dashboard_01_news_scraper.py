from pathlib import Path
import sys
import runpy

# 프로젝트 루트 경로 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT.parent))

TARGET = ROOT / "dashboard_01_news_scraper.py"
runpy.run_path(str(TARGET))
