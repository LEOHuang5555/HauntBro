"""
Database seeding script for HauntBro development and testing.
"""

import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session

from database.connection import db_manager, init_database
from database.models import User, Story, SearchLog, UserFavorite, StoryRating, ScrapingJob
from auth.models import AuthManager


fake = Faker()


def seed_users(db: Session, count: int = 10):
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


def seed_stories(db: Session, count: int = 50):
    """Seed stories table with fake ghost stories."""
    print(f"Seeding {count} stories...")
    
    sources = ["ptt_marvel", "reddit_ghoststories"]
    ghost_story_themes = [
        "haunted house", "ghost encounter", "supernatural experience", "paranormal activity",
        "possessed object", "cemetery ghost", "school ghost", "hospital ghost", "forest spirit",
        "urban legend", "family curse", "demon encounter", "poltergeist", "shadow figure"
    ]
    
    stories = []
    for i in range(count):
        source = random.choice(sources)
        theme = random.choice(ghost_story_themes)
        
        story_data = {
            "title": f"Ghost Story: {fake.sentence(nb_words=6)}",
            "content": f"This is a {theme} story. {fake.text(max_nb_chars=2000)}",
            "source": source,
            "source_url": fake.url(),
            "author": fake.user_name(),
            "post_date": fake.date_time_between(start_date="-2y", end_date="now"),
            "scraped_at": fake.date_time_between(start_date="-1y", end_date="now"),
            "word_count": random.randint(100, 2000),
            "reading_time_minutes": random.randint(1, 10),
            "tags": random.sample(["horror", "ghost", "paranormal", "supernatural", "scary", "mystery", "true-story"], 
                                random.randint(1, 4)),
            "upvotes": random.randint(0, 100),
            "downvotes": random.randint(0, 20),
            "comments_count": random.randint(0, 50),
            "is_nsfw": random.choice([True, False]) if random.random() < 0.1 else False,
            "content_warning": "Contains supernatural themes" if random.random() < 0.3 else None
        }
        
        story = Story(**story_data)
        stories.append(story)
        db.add(story)
    
    db.commit()
    print(f"✓ Created {count} stories")
    return stories


def seed_search_logs(db: Session, users: list, stories: list, count: int = 100):
    """Seed search logs with fake search data."""
    print(f"Seeding {count} search logs...")
    
    search_queries = [
        "ghost", "haunted house", "supernatural", "scary story", "paranormal",
        "demon", "poltergeist", "shadow figure", "cemetery", "haunted school",
        "possessed object", "family curse", "urban legend", "true ghost story"
    ]
    
    search_types = ["keyword", "semantic", "hybrid"]
    
    for i in range(count):
        user = random.choice(users) if random.random() < 0.7 else None  # 70% chance of logged user
        query = random.choice(search_queries)
        
        # Simulate clicked results
        clicked_stories = random.sample(stories, random.randint(0, 5))
        clicked_results = [story.id for story in clicked_stories]
        
        search_log_data = {
            "user_id": user.id if user else None,
            "query": query,
            "results_count": random.randint(0, 20),
            "search_type": random.choice(search_types),
            "executed_at": fake.date_time_between(start_date="-6m", end_date="now"),
            "execution_time_ms": random.randint(50, 500),
            "clicked_results": clicked_results,
            "source_filter": random.choice(["ptt_marvel", "reddit_ghoststories"]) if random.random() < 0.3 else None,
        }
        
        search_log = SearchLog(**search_log_data)
        db.add(search_log)
    
    db.commit()
    print(f"✓ Created {count} search logs")


def seed_user_favorites(db: Session, users: list, stories: list, count: int = 30):
    """Seed user favorites."""
    print(f"Seeding {count} user favorites...")
    
    created_favorites = set()
    
    for i in range(count):
        user = random.choice(users)
        story = random.choice(stories)
        
        # Ensure unique user-story combinations
        if (user.id, story.id) in created_favorites:
            continue
        
        created_favorites.add((user.id, story.id))
        
        favorite_data = {
            "user_id": user.id,
            "story_id": story.id,
            "created_at": fake.date_time_between(start_date="-6m", end_date="now"),
            "notes": fake.sentence() if random.random() < 0.5 else None
        }
        
        favorite = UserFavorite(**favorite_data)
        db.add(favorite)
    
    db.commit()
    print(f"✓ Created {len(created_favorites)} user favorites")


def seed_story_ratings(db: Session, users: list, stories: list, count: int = 80):
    """Seed story ratings."""
    print(f"Seeding {count} story ratings...")
    
    created_ratings = set()
    
    for i in range(count):
        user = random.choice(users)
        story = random.choice(stories)
        
        # Ensure unique user-story combinations
        if (user.id, story.id) in created_ratings:
            continue
        
        created_ratings.add((user.id, story.id))
        
        rating_data = {
            "user_id": user.id,
            "story_id": story.id,
            "rating": random.randint(1, 5),
            "created_at": fake.date_time_between(start_date="-6m", end_date="now")
        }
        
        rating = StoryRating(**rating_data)
        db.add(rating)
    
    db.commit()
    print(f"✓ Created {len(created_ratings)} story ratings")


def seed_scraping_jobs(db: Session, count: int = 20):
    """Seed scraping jobs."""
    print(f"Seeding {count} scraping jobs...")
    
    sources = ["ptt_marvel", "reddit_ghoststories"]
    statuses = ["completed", "failed", "pending", "running"]
    
    for i in range(count):
        status = random.choice(statuses)
        started_at = fake.date_time_between(start_date="-1y", end_date="now")
        
        job_data = {
            "source": random.choice(sources),
            "status": status,
            "started_at": started_at,
            "completed_at": started_at + timedelta(minutes=random.randint(5, 60)) if status == "completed" else None,
            "stories_scraped": random.randint(0, 50) if status == "completed" else 0,
            "errors_count": random.randint(0, 5) if status == "failed" else 0,
            "error_log": fake.text(max_nb_chars=200) if status == "failed" else None
        }
        
        job = ScrapingJob(**job_data)
        db.add(job)
    
    db.commit()
    print(f"✓ Created {count} scraping jobs")


def seed_database():
    """Seed the entire database with test data."""
    print("🌱 Starting database seeding...")
    
    # Initialize database
    init_database()
    
    with db_manager.get_session() as db:
        # Check if database is already seeded
        user_count = db.query(User).count()
        if user_count > 0:
            print(f"Database already contains {user_count} users. Skipping seeding.")
            print("Use --force to re-seed or clear the database first.")
            return
        
        # Seed in order due to foreign key dependencies
        users = seed_users(db, count=10)
        stories = seed_stories(db, count=50)
        seed_search_logs(db, users, stories, count=100)
        seed_user_favorites(db, users, stories, count=30)
        seed_story_ratings(db, users, stories, count=80)
        seed_scraping_jobs(db, count=20)
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nTest user credentials:")
        print("Username: testuser")
        print("Password: password123")
        print("\nYou can now start the application and test with the seeded data.")


def clear_database():
    """Clear all data from the database."""
    print("🗑️  Clearing database...")
    
    with db_manager.get_session() as db:
        # Delete in reverse order of dependencies
        db.query(ScrapingJob).delete()
        db.query(StoryRating).delete()
        db.query(UserFavorite).delete()
        db.query(SearchLog).delete()
        db.query(Story).delete()
        db.query(User).delete()
        db.commit()
        
        print("✓ Database cleared successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        clear_database()
    elif len(sys.argv) > 1 and sys.argv[1] == "--force":
        clear_database()
        seed_database()
    else:
        seed_database()