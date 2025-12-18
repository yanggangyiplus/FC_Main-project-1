#!/usr/bin/env python3
"""전체 파이프라인 테스트 스크립트"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("=" * 80)
    print("전체 파이프라인 실행 시작")
    print("=" * 80)

    # workflows/blog_workflow.py의 함수 사용
    from workflows.blog_workflow import run_workflow

    # 테스트용 카테고리와 토픽
    category = "IT/과학"
    topic = "인공지능 최신 동향"

    print(f"카테고리: {category}")
    print(f"토픽: {topic}")
    print()

    result = run_workflow(category=category, topic=topic)

    print("=" * 80)
    print("파이프라인 실행 완료")
    print(f"결과: {result}")
    print("=" * 80)

    return result

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n에러 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
