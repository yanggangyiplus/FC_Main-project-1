# -*- coding: utf-8 -*-
"""
Test Runner - Saves scraping results for reuse in subsequent tests
Usage:
    python test_runner.py                    # Full workflow (scraping + all)
    python test_runner.py --skip-scrape      # Skip scraping, use saved data
    python test_runner.py --from-blog        # Start from blog generation (skip scrape + RAG)
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger

# Test data file path
TEST_DATA_FILE = Path(__file__).parent / "test_data" / "test_state.json"


def save_test_state(state: dict):
    """Save test state to JSON file"""
    TEST_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert non-serializable objects
    save_data = {
        "topic": state.get("topic", ""),
        "category": state.get("category", ""),
        "rag_context": state.get("rag_context", ""),
        "blog_content": state.get("blog_content", ""),
        "blog_title": state.get("blog_title", ""),
        "created_at": datetime.now().isoformat(),
    }
    
    # Save articles if present
    if "articles" in state and state["articles"]:
        articles_data = []
        for article in state["articles"]:
            if hasattr(article, "__dict__"):
                articles_data.append(article.__dict__)
            elif isinstance(article, dict):
                articles_data.append(article)
        save_data["articles"] = articles_data
    
    with open(TEST_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Test state saved to {TEST_DATA_FILE}")


def load_test_state() -> dict:
    """Load test state from JSON file"""
    if not TEST_DATA_FILE.exists():
        logger.warning(f"No saved test state found at {TEST_DATA_FILE}")
        return None
    
    with open(TEST_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not data.get("topic"):
        logger.warning("Saved test state is empty, need to run full workflow first")
        return None
    
    logger.info(f"Loaded test state from {TEST_DATA_FILE}")
    logger.info(f"  Topic: {data.get('topic', '')[:50]}...")
    logger.info(f"  Created: {data.get('created_at', 'unknown')}")
    
    return data


def run_full_workflow(category: str = "it_science", topic: str = "IT Technology News"):
    """Run full workflow and save state"""
    from workflows.blog_workflow import BlogWorkflow
    
    workflow = BlogWorkflow()
    
    # Hook to save state after scraping
    original_run = workflow.run_workflow
    
    def run_with_save(*args, **kwargs):
        result = original_run(*args, **kwargs)
        
        # Save the final state
        if result:
            save_test_state(result)
        
        return result
    
    # Run workflow
    result = workflow.run_workflow(category=category, topic=topic)
    
    if result:
        save_test_state(result)
    
    return result


def run_from_blog_generation(skip_publish: bool = False):
    """Run workflow starting from blog generation using saved data"""
    import importlib
    
    saved_state = load_test_state()
    if not saved_state:
        logger.error("No saved state found. Run full workflow first: python test_runner.py")
        return None
    
    # Import modules
    blog_gen_module = importlib.import_module("modules.03_blog_generator.blog_generator")
    critic_module = importlib.import_module("modules.04_critic_qa.critic")
    humanizer_module = importlib.import_module("modules.05_humanizer.humanizer")
    img_gen_module = importlib.import_module("modules.06_image_generator.image_generator")
    publisher_module = importlib.import_module("modules.07_blog_publisher.publisher")
    
    BlogGenerator = blog_gen_module.BlogGenerator
    BlogCritic = critic_module.BlogCritic
    Humanizer = humanizer_module.Humanizer
    GoogleImagenGenerator = img_gen_module.GoogleImagenGenerator
    NaverBlogPublisher = publisher_module.NaverBlogPublisher
    
    topic = saved_state["topic"]
    category = saved_state["category"]
    rag_context = saved_state["rag_context"]
    
    logger.info(f"=== Starting from Blog Generation ===")
    logger.info(f"Topic: {topic}")
    logger.info(f"Category: {category}")
    logger.info(f"RAG Context length: {len(rag_context)} chars")
    
    # 1. Blog Generation
    logger.info("\n[1/5] Generating blog...")
    blog_gen = BlogGenerator()
    blog_result = blog_gen.generate_blog(topic=topic, context=rag_context)
    blog_content = blog_result.get("html", "")
    logger.info(f"Blog generated: {len(blog_content)} chars")
    
    # 2. Quality Evaluation
    logger.info("\n[2/5] Evaluating blog quality...")
    critic = BlogCritic()
    eval_result = critic.evaluate(topic=topic, blog_content=blog_content, context=rag_context)
    logger.info(f"Score: {eval_result.score}/100, Pass: {eval_result.passed}")
    
    if not eval_result.passed:
        logger.warning(f"Quality check failed. Feedback: {eval_result.feedback}")
        # Continue anyway for testing
    
    # 3. Humanize
    logger.info("\n[3/5] Humanizing blog...")
    humanizer = Humanizer()
    humanized_content = humanizer.humanize(blog_content)
    logger.info(f"Humanized: {len(humanized_content)} chars")
    
    # 4. Image Generation
    logger.info("\n[4/5] Generating images...")
    img_gen = GoogleImagenGenerator(category=category)
    img_gen._rag_context = rag_context
    
    placeholders = blog_gen.extract_image_placeholders(humanized_content)
    logger.info(f"Found {len(placeholders)} image placeholders")
    
    images = img_gen.generate_images_for_blog(
        blog_topic=topic,
        blog_content=humanized_content,
        num_images=len(placeholders)
    )
    logger.info(f"Generated {len(images)} images")
    
    # Show image paths
    for i, img_path in enumerate(images):
        logger.info(f"  Image {i+1}: {img_path}")
    
    # 5. Publish (optional)
    if not skip_publish:
        logger.info("\n[5/5] Publishing blog...")
        publisher = NaverBlogPublisher()
        result = publisher.publish(
            title=topic,
            content=humanized_content,
            images=images
        )
        logger.info(f"Publish result: {result}")
    else:
        logger.info("\n[5/5] Skipping publish (--skip-publish flag)")
    
    return {
        "topic": topic,
        "blog_content": humanized_content,
        "images": images,
        "score": eval_result.score
    }


def main():
    parser = argparse.ArgumentParser(description="Blog Workflow Test Runner")
    parser.add_argument("--skip-scrape", action="store_true", 
                        help="Skip scraping, use saved data")
    parser.add_argument("--from-blog", action="store_true",
                        help="Start from blog generation (skip scrape + RAG)")
    parser.add_argument("--skip-publish", action="store_true",
                        help="Skip blog publishing")
    parser.add_argument("--category", type=str, default="it_science",
                        help="News category (default: it_science)")
    parser.add_argument("--topic", type=str, default="IT Technology News",
                        help="Initial topic (default: IT Technology News)")
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Blog Workflow Test Runner")
    print("=" * 60)
    
    if args.from_blog:
        print("Mode: Starting from Blog Generation (using saved data)")
        run_from_blog_generation(skip_publish=args.skip_publish)
    elif args.skip_scrape:
        print("Mode: Skip Scraping (using saved RAG context)")
        # TODO: Implement partial workflow
        logger.info("Not implemented yet - use --from-blog instead")
    else:
        print(f"Mode: Full Workflow")
        print(f"Category: {args.category}")
        run_full_workflow(category=args.category, topic=args.topic)


if __name__ == "__main__":
    main()

