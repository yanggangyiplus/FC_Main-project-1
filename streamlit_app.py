"""
Streamlit Cloud 배포용 엔트리 포인트.
기존 `dashboards/workflow_dashboard.py`를 그대로 실행합니다.
"""
from pathlib import Path
import sys
import runpy
import streamlit as st

# 프로젝트 루트 및 타겟 대시보드 경로 설정
ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "dashboards" / "workflow_dashboard.py"

# 모듈 검색 경로에 프로젝트 루트 추가
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 대시보드 파일 존재 여부 확인
if not TARGET.exists():
    st.error(f"대시보드 파일을 찾을 수 없습니다: {TARGET}")
    st.stop()

# 워크플로우 대시보드 실행
runpy.run_path(str(TARGET), run_name="__main__")
