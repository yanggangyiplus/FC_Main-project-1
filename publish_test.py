"""
네이버 블로그 발행 테스트 스크립트
- 이미지가 삽입된 HTML을 네이버 블로그에 발행
- 네이버 스마트에디터 직접 제어 방식 사용
"""
import sys
import importlib.util
from pathlib import Path
import json

# 모듈 동적 로드 (숫자로 시작하는 폴더명 처리)
spec = importlib.util.spec_from_file_location(
    'publisher', 
    'modules/07_blog_publisher/publisher.py'
)
publisher_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher_module)
NaverBlogPublisher = publisher_module.NaverBlogPublisher


def main():
    """네이버 블로그 발행 실행"""
    
    # 최신 humanized HTML 파일 (economy 카테고리)
    html_path = Path(r"f:\CLASSHUB\OneDrive\Desktop\FC_Main-project-1\data\generated_blogs\economy\humanized_20251217_003338.html")
    
    # 이미지 목록 직접 지정 (economy 카테고리 최신 이미지)
    image_dir = Path(r"f:\CLASSHUB\OneDrive\Desktop\FC_Main-project-1\data\images\economy")
    image_files = [
        "imagen_20251217_003239_0.png",
        "imagen_20251217_003251_1.png",
        "imagen_20251217_003308_2.png"
    ]
    
    # 이미지 매핑 파일 (없으면 직접 생성)
    mapping_path = Path(r"f:\CLASSHUB\OneDrive\Desktop\FC_Main-project-1\data\metadata\economy\blog_image_mapping.json")
    
    # 파일 존재 확인
    if not html_path.exists():
        print(f"[ERROR] HTML 파일을 찾을 수 없습니다: {html_path}")
        return None
    
    # HTML 로드
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 이미지 리스트 생성
    images = []
    for i, img_file in enumerate(image_files):
        img_path = image_dir / img_file
        if img_path.exists():
            images.append({
                'index': i,
                'local_path': str(img_path),
                'alt': f'이미지 {i+1}'
            })
            print(f"[OK] 이미지 {i+1}: {img_file}")
        else:
            print(f"[WARN] 이미지 {i+1}: 파일 없음 - {img_path}")
    
    # 블로그 제목
    blog_title = "격변하는 2025년 대한민국 정치: 내란 특검 종료와 여야 갈등 심화"
    
    print()
    print("=" * 60)
    print("네이버 블로그 발행 테스트 (STEP 7)")
    print("=" * 60)
    print(f"제목: {blog_title}")
    print(f"이미지: {len(images)}개")
    print(f"HTML 길이: {len(html_content)}자")
    print()
    
    # 발행기 초기화 (headless=False로 브라우저 표시)
    print("[INFO] 브라우저 시작 중...")
    publisher = NaverBlogPublisher(headless=False)
    
    # 발행 실행 (content 파라미터 사용 - 워크플로우와 동일)
    print("[INFO] 발행 시작...")
    result = publisher.publish(
        title=blog_title,
        content=html_content,  # HTML 콘텐츠 직접 전달
        images=images,
        category='economy'  # 경제 카테고리
    )
    
    print()
    print("=" * 60)
    print("발행 결과")
    print("=" * 60)
    if result.get('success'):
        print(f"[성공] URL: {result.get('url', 'N/A')}")
    else:
        print(f"[실패] 오류: {result.get('error', '알 수 없는 오류')}")
    
    return result


if __name__ == "__main__":
    main()
