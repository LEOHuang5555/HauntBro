"""
Database seeding script for HauntBro - Medallion Architecture
Seeds Bronze-Silver-Gold layers with realistic test data.
"""

import random
import re
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

from database.connection import db_manager, init_database
from database.models import (
    # Bronze Layer
    BronzeStory,
    # Silver Layer
    SilverStory, SilverStoryChunk,
    # Gold Layer
    GoldStoryPerformance,
    # User Layer
    User, UserFavorite, StoryRating,
    # Analytics Layer
    SearchInteraction, UserReadingBehavior,
    # Pipeline Layer
    ScrapingPipelineMetrics
)
from auth.models import AuthManager


fake = Faker()


def seed_users(db: Session, count: int = 15):
    """Seed users table with fake data."""
    print(f"Seeding {count} users...")
    
    users = []
    for i in range(count):
        user_data = {
            "username": fake.user_name(),
            "email": fake.email(),
            "password_hash": AuthManager.get_password_hash("password123"),
            "is_active": True,
            "created_at": fake.date_time_between(start_date="-1y", end_date="now"),
            "last_login": fake.date_time_between(start_date="-30d", end_date="now") if random.choice([True, False]) else None
        }
        
        user = User(**user_data)
        users.append(user)
        db.add(user)
    
    db.commit()
    print(f"✓ Created {count} users")
    return users


def seed_bronze_stories(db: Session, count: int = 100):
    """Seed bronze layer with raw scraped stories."""
    print(f"Seeding {count} bronze stories...")
    
    sources = ["ptt_marvel", "reddit_ghoststories"]
    ghost_story_themes = [
        "haunted house", "ghost encounter", "supernatural experience", "paranormal activity",
        "possessed object", "cemetery ghost", "school ghost", "hospital ghost", "forest spirit",
        "urban legend", "family curse", "demon encounter", "poltergeist", "shadow figure",
        "elevator ghost", "mirror spirit", "phantom call", "cursed doll", "ghostly apparition"
    ]
    
    bronze_stories = []
    for i in range(count):
        source = random.choice(sources)
        theme = random.choice(ghost_story_themes)
        
        # Generate story content
        title = f"The {theme.title()} - {fake.sentence(nb_words=3)}"
        content = f"This is a terrifying {theme} story that happened to me. {fake.text(max_nb_chars=3000)}"
        
        # Generate realistic raw metadata
        raw_metadata = {
            "upvotes": random.randint(0, 500),
            "downvotes": random.randint(0, 50),
            "comments_count": random.randint(0, 200),
            "is_nsfw": random.choice([True, False]) if random.random() < 0.1 else False,
            "content_warning": "Contains supernatural themes" if random.random() < 0.3 else None,
            "tags": random.sample(["horror", "ghost", "paranormal", "supernatural", "scary", "mystery", "true-story"], 
                                random.randint(1, 4)),
            "scraped_url": fake.url(),
            "scraped_timestamp": fake.date_time_between(start_date="-1y", end_date="now").isoformat()
        }
        
        story_data = {
            "title": title,
            "content": content,
            "source": source,
            "source_url": fake.url(),
            "author": fake.user_name(),
            "post_date": fake.date_time_between(start_date="-2y", end_date="now"),
            "scraped_at": fake.date_time_between(start_date="-1y", end_date="now"),
            "raw_metadata": raw_metadata
        }
        
        story = BronzeStory(**story_data)
        bronze_stories.append(story)
        db.add(story)
    
    db.commit()
    print(f"✓ Created {count} bronze stories")
    return bronze_stories


def seed_silver_stories(db: Session, bronze_stories: list):
    """Seed silver layer with cleaned story metadata."""
    print(f"Seeding {len(bronze_stories)} silver stories...")
    
    silver_stories = []
    for bronze_story in bronze_stories:
        # Clean content (remove excessive punctuation, normalize text)
        cleaned_content = re.sub(r'[!]{2,}', '!', bronze_story.content)
        cleaned_content = re.sub(r'[?]{2,}', '?', cleaned_content)
        cleaned_content = re.sub(r'[.]{3,}', '...', cleaned_content)
        
        # Extract tags from raw metadata
        tags = bronze_story.raw_metadata.get('tags', [])
        
        # Calculate reading metrics
        word_count = len(cleaned_content.split())
        reading_time_minutes = max(1, word_count // 200)  # Assume 200 words per minute
        
        story_data = {
            "bronze_story_id": bronze_story.id,
            "title": bronze_story.title,
            "cleaned_content": cleaned_content,
            "author": bronze_story.author,
            "post_date": bronze_story.post_date,
            "tags": tags,
            "reading_time_minutes": reading_time_minutes,
            "word_count": word_count
        }
        
        story = SilverStory(**story_data)
        silver_stories.append(story)
        db.add(story)
    
    db.commit()
    print(f"✓ Created {len(bronze_stories)} silver stories")
    return silver_stories


def seed_silver_story_chunks(db: Session, silver_stories: list, chunks_per_story: int = 3):
    """Seed silver layer with story chunks for RAG."""
    print(f"Seeding story chunks ({chunks_per_story} per story)...")
    
    chunk_count = 0
    for silver_story in silver_stories:
        content = silver_story.cleaned_content
        sentences = content.split('. ')
        
        # Create chunks from sentences
        chunk_size = max(1, len(sentences) // chunks_per_story)
        
        for i in range(chunks_per_story):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, len(sentences))
            
            if start_idx >= len(sentences):
                break
                
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = '. '.join(chunk_sentences)
            
            # Create context with surrounding sentences
            context_start = max(0, start_idx - 1)
            context_end = min(len(sentences), end_idx + 1)
            context_sentences = sentences[context_start:context_end]
            chunk_context = '. '.join(context_sentences)
            
            chunk_data = {
                "bronze_story_id": silver_story.bronze_story_id,
                "chunk_text": chunk_text,
                "chunk_context": chunk_context,
                "chunk_order": i + 1,
                "embedding": None  # Will be populated by embedding service later
            }
            
            chunk = SilverStoryChunk(**chunk_data)
            db.add(chunk)
            chunk_count += 1
    
    db.commit()
    print(f"✓ Created {chunk_count} story chunks")


def seed_gold_story_performance(db: Session, bronze_stories: list):
    """Seed gold layer with story performance metrics."""
    print(f"Seeding performance metrics for {len(bronze_stories)} stories...")
    
    for bronze_story in bronze_stories:
        # Generate realistic performance metrics
        total_reads = random.randint(0, 10000)
        unique_readers = int(total_reads * random.uniform(0.3, 0.8))  # 30-80% unique readers
        
        performance_data = {
            "story_id": bronze_story.id,
            "total_reads": total_reads,
            "unique_readers": unique_readers,
            "avg_user_rating": round(random.uniform(1.0, 5.0), 2),
            "favorites_count": random.randint(0, int(total_reads * 0.1)),  # Up to 10% of reads
            "search_impressions": random.randint(total_reads, total_reads * 3),
            "search_clicks": random.randint(int(total_reads * 0.5), total_reads),
            "last_updated": fake.date_time_between(start_date="-30d", end_date="now")
        }
        
        performance = GoldStoryPerformance(**performance_data)
        db.add(performance)
    
    db.commit()
    print(f"✓ Created performance metrics for {len(bronze_stories)} stories")


def seed_search_interactions(db: Session, users: list, bronze_stories: list, count: int = 500):
    """Seed search interactions with realistic search patterns."""
    print(f"Seeding {count} search interactions...")
    
    search_queries = [
        "ghost story", "haunted house", "supernatural", "scary story", "paranormal activity",
        "demon encounter", "poltergeist", "shadow figure", "cemetery ghost", "school ghost",
        "possessed object", "family curse", "urban legend", "true ghost story", "horror",
        "spooky", "creepy", "phantom", "spirit", "apparition", "haunting", "cursed",
        "nightmare", "terrifying", "bone-chilling", "ghostly encounter", "supernatural event"
    ]
    
    search_types = ["keyword", "semantic", "hybrid"]
    
    interactions = []
    for i in range(count):
        user = random.choice(users) if random.random() < 0.7 else None  # 70% logged in users
        query = random.choice(search_queries)
        
        # Simulate search results
        result_stories = random.sample(bronze_stories, min(20, len(bronze_stories)))
        results_shown = [story.id for story in result_stories]
        
        # Simulate clicks (users typically click on first few results)
        click_count = random.randint(0, 5)
        if click_count > 0:
            clicked_stories = result_stories[:click_count]
            results_clicked = [story.id for story in clicked_stories]
            click_positions = list(range(1, click_count + 1))
            time_to_first_click = random.randint(500, 5000)  # 0.5-5 seconds
        else:
            results_clicked = []
            click_positions = []
            time_to_first_click = None
        
        interaction_data = {
            "user_id": user.id if user else None,
            "session_id": fake.uuid4(),
            "query": query,
            "search_timestamp": fake.date_time_between(start_date="-6m", end_date="now"),
            "results_shown": results_shown,
            "results_clicked": results_clicked,
            "click_positions": click_positions,
            "time_to_first_click": time_to_first_click,
            "search_type": random.choice(search_types),
            "execution_time_ms": random.randint(50, 1000)
        }
        
        interaction = SearchInteraction(**interaction_data)
        interactions.append(interaction)
        db.add(interaction)
    
    db.commit()
    print(f"✓ Created {count} search interactions")
    return interactions


def seed_user_reading_behavior(db: Session, users: list, bronze_stories: list, count: int = 800):
    """Seed user reading behavior analytics."""
    print(f"Seeding {count} reading behavior records...")
    
    for i in range(count):
        user = random.choice(users)
        story = random.choice(bronze_stories)
        
        # Simulate reading behavior
        reading_duration = random.randint(30, 1800)  # 30 seconds to 30 minutes
        scroll_depth = random.uniform(0.1, 1.0)  # 10% to 100% of content
        bounce_rate = reading_duration < 60  # Less than 1 minute = bounce
        
        behavior_data = {
            "user_id": user.id,
            "story_id": story.id,
            "reading_start_time": fake.date_time_between(start_date="-6m", end_date="now"),
            "reading_duration": reading_duration,
            "return_visits": random.randint(1, 5),
            "favorited": random.choice([True, False]) if random.random() < 0.1 else False,
            "shared": random.choice([True, False]) if random.random() < 0.05 else False,
            "scroll_depth": scroll_depth,
            "bounce_rate": bounce_rate
        }
        
        behavior = UserReadingBehavior(**behavior_data)
        db.add(behavior)
    
    db.commit()
    print(f"✓ Created {count} reading behavior records")


def seed_user_favorites(db: Session, users: list, bronze_stories: list, count: int = 100):
    """Seed user favorites."""
    print(f"Seeding {count} user favorites...")
    
    created_favorites = set()
    
    for i in range(count):
        user = random.choice(users)
        story = random.choice(bronze_stories)
        
        # Ensure unique user-story combinations
        if (user.id, story.id) in created_favorites:
            continue
        
        created_favorites.add((user.id, story.id))
        
        favorite_data = {
            "user_id": user.id,
            "story_id": story.id,
            "created_at": fake.date_time_between(start_date="-6m", end_date="now"),
            "notes": fake.sentence() if random.random() < 0.3 else None
        }
        
        favorite = UserFavorite(**favorite_data)
        db.add(favorite)
    
    db.commit()
    print(f"✓ Created {len(created_favorites)} user favorites")


def seed_story_ratings(db: Session, users: list, bronze_stories: list, count: int = 200):
    """Seed story ratings."""
    print(f"Seeding {count} story ratings...")
    
    created_ratings = set()
    
    for i in range(count):
        user = random.choice(users)
        story = random.choice(bronze_stories)
        
        # Ensure unique user-story combinations
        if (user.id, story.id) in created_ratings:
            continue
        
        created_ratings.add((user.id, story.id))
        
        # Generate ratings with slight bias towards higher ratings
        rating = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 20, 35, 30])[0]
        
        rating_data = {
            "user_id": user.id,
            "story_id": story.id,
            "rating": rating,
            "created_at": fake.date_time_between(start_date="-6m", end_date="now")
        }
        
        rating_obj = StoryRating(**rating_data)
        db.add(rating_obj)
    
    db.commit()
    print(f"✓ Created {len(created_ratings)} story ratings")


def seed_scraping_pipeline_metrics(db: Session, count: int = 50):
    """Seed scraping pipeline metrics."""
    print(f"Seeding {count} pipeline metrics...")
    
    sources = ["ptt_marvel", "reddit_ghoststories"]
    statuses = ["completed", "failed", "running"]
    
    for i in range(count):
        source = random.choice(sources)
        stories_discovered = random.randint(10, 200)
        stories_new = random.randint(0, int(stories_discovered * 0.8))
        stories_updated = random.randint(0, int(stories_discovered * 0.2))
        
        metrics_data = {
            "airflow_dag_run_id": f"scrape_{source}_{fake.uuid4()}",
            "source_name": source,
            "stories_discovered": stories_discovered,
            "stories_new": stories_new,
            "stories_updated": stories_updated,
            "duplicate_rate": round(random.uniform(0.1, 0.4), 3),
            "processing_time_seconds": random.randint(60, 3600),
            "errors_count": random.randint(0, 5),
            "error_log": fake.text(max_nb_chars=200) if random.random() < 0.3 else None,
            "created_at": fake.date_time_between(start_date="-1y", end_date="now")
        }
        
        metrics = ScrapingPipelineMetrics(**metrics_data)
        db.add(metrics)
    
    db.commit()
    print(f"✓ Created {count} pipeline metrics")


def seed_database():
    """Seed the entire medallion architecture database with test data."""
    print("🌱 Starting medallion architecture database seeding...")
    
    # Initialize database
    init_database()
    
    with db_manager.get_session() as db:
        # Check if database is already seeded
        user_count = db.query(User).count()
        if user_count > 0:
            print(f"Database already contains {user_count} users. Skipping seeding.")
            print("Use --force to re-seed or clear the database first.")
            return
        
        # Seed in dependency order
        print("\n📊 Seeding Bronze-Silver-Gold layers...")
        
        # User layer (independent)
        users = seed_users(db, count=15)
        
        # Bronze layer (raw data)
        bronze_stories = seed_bronze_stories(db, count=100)
        
        # Silver layer (processed data)
        silver_stories = seed_silver_stories(db, bronze_stories)
        seed_silver_story_chunks(db, silver_stories, chunks_per_story=4)
        
        # Gold layer (business metrics)
        seed_gold_story_performance(db, bronze_stories)
        
        # Analytics layer (user behavior)
        search_interactions = seed_search_interactions(db, users, bronze_stories, count=500)
        seed_user_reading_behavior(db, users, bronze_stories, count=800)
        
        # User interactions
        seed_user_favorites(db, users, bronze_stories, count=100)
        seed_story_ratings(db, users, bronze_stories, count=200)
        
        # Pipeline layer (data engineering)
        seed_scraping_pipeline_metrics(db, count=50)
        
        print("\n🎉 Medallion architecture seeding completed successfully!")
        print("\nDatabase Statistics:")
        print(f"- Users: {len(users)}")
        print(f"- Bronze Stories: {len(bronze_stories)}")
        print(f"- Silver Stories: {len(silver_stories)}")
        print(f"- Story Chunks: {len(silver_stories) * 4} (avg)")
        print(f"- Search Interactions: 500")
        print(f"- Reading Behaviors: 800")
        print(f"- User Favorites: 100")
        print(f"- Story Ratings: 200")
        print(f"- Pipeline Metrics: 50")
        
        print("\nTest user credentials:")
        print("Username: testuser")
        print("Password: password123")
        print("\nYou can now explore the medallion architecture!")


def clear_database():
    """Clear all data from the medallion architecture database."""
    print("🗑️  Clearing medallion architecture database...")
    
    with db_manager.get_session() as db:
        # Delete in reverse order of dependencies
        db.query(ScrapingPipelineMetrics).delete()
        db.query(UserReadingBehavior).delete()
        db.query(SearchInteraction).delete()
        db.query(StoryRating).delete()
        db.query(UserFavorite).delete()
        db.query(GoldStoryPerformance).delete()
        db.query(SilverStoryChunk).delete()
        db.query(SilverStory).delete()
        db.query(BronzeStory).delete()
        db.query(User).delete()
        db.commit()
        
        print("✓ Medallion architecture database cleared successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "--force":
        clear_database()
        seed_database()
    else:
        seed_database()