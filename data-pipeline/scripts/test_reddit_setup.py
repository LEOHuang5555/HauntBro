"""
Test script to verify Reddit scraper setup and database connectivity.
"""

import os
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root / 'backend'))
sys.path.append(str(project_root / 'data-pipeline'))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        from scrapers.reddit_scraper import RedditScraper
        print("✅ Reddit scraper import successful")
    except ImportError as e:
        print(f"❌ Reddit scraper import failed: {e}")
        return False
    
    try:
        from etl.reddit_etl import RedditETLPipeline
        print("✅ ETL pipeline import successful")
    except ImportError as e:
        print(f"❌ ETL pipeline import failed: {e}")
        return False
    
    try:
        from app.database.models import BronzeStory, SilverStory
        print("✅ Database models import successful")
    except ImportError as e:
        print(f"❌ Database models import failed: {e}")
        return False
    
    return True

def test_reddit_credentials():
    """Test Reddit API credentials."""
    print("\nTesting Reddit credentials...")
    
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    user_agent = os.getenv('REDDIT_USER_AGENT')
    
    if client_id and client_secret:
        print("✅ Reddit API credentials found")
        if user_agent:
            print("✅ User agent configured")
        else:
            print("⚠️  User agent not set (will use default)")
        return True
    else:
        print("❌ Reddit API credentials missing")
        print("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables")
        return False

def test_database_connection():
    """Test database connectivity."""
    print("\nTesting database connection...")
    
    try:
        from app.database.connection import get_db_url
        from sqlalchemy import create_engine
        
        db_url = get_db_url()
        engine = create_engine(db_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Database connection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_reddit_api():
    """Test Reddit API connectivity."""
    print("\nTesting Reddit API...")
    
    try:
        from scrapers.reddit_scraper import RedditScraper
        
        scraper = RedditScraper()
        if scraper.reddit:
            # Try to fetch 1 story
            stories = scraper.get_nosleep_stories(limit=1, time_filter='hot')
            if stories:
                print(f"✅ Reddit API test successful - fetched sample story")
                print(f"   Title: {stories[0]['title'][:50]}...")
                return True
            else:
                print("❌ No stories returned from Reddit API")
                return False
        else:
            print("❌ Reddit client not initialized")
            return False
            
    except Exception as e:
        print(f"❌ Reddit API test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 HauntBro Reddit Setup Test")
    print("=" * 40)
    
    tests = [
        ("Imports", test_imports),
        ("Reddit Credentials", test_reddit_credentials),
        ("Database Connection", test_database_connection),
        ("Reddit API", test_reddit_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name + ":"))
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your setup is ready for Reddit scraping.")
        print("\nNext steps:")
        print("1. Run: python data-pipeline/scripts/collect_reddit_stories.py --test")
        print("2. For full collection: python data-pipeline/scripts/collect_reddit_stories.py --count 1000")
    else:
        print("\n😞 Some tests failed. Please fix the issues above before proceeding.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)