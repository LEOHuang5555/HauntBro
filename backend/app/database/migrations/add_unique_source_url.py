"""Add unique constraint on source_url to prevent duplicate stories.

This migration adds a unique constraint on the source_url column in the bronze_stories table
to prevent duplicate stories from being stored in the database.

Created: 2025-07-20
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine):
    """Add unique constraint on source_url."""
    with engine.connect() as conn:
        # First, remove any existing duplicates (keep the oldest entry)
        conn.execute(text("""
            DELETE FROM bronze_stories 
            WHERE id NOT IN (
                SELECT DISTINCT ON (source_url) id 
                FROM bronze_stories 
                ORDER BY source_url, scraped_at ASC
            )
            AND source_url IS NOT NULL 
            AND source_url != '';
        """))
        
        # Add the unique constraint
        conn.execute(text("""
            ALTER TABLE bronze_stories 
            ADD CONSTRAINT unique_source_url UNIQUE (source_url);
        """))
        
        conn.commit()
        print("✓ Added unique constraint on source_url")


def downgrade(engine: Engine):
    """Remove unique constraint on source_url."""
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE bronze_stories 
            DROP CONSTRAINT IF EXISTS unique_source_url;
        """))
        
        conn.commit()
        print("✓ Removed unique constraint on source_url")


def main():
    """Run migration manually."""
    import sys
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Add backend to path
    backend_root = Path(__file__).parent.parent.parent
    sys.path.append(str(backend_root))
    
    from sqlalchemy import create_engine
    
    # Get database URL directly
    database_url = os.getenv(
        'DATABASE_URL',
        'postgresql+psycopg2://hbadmin:dj3jkp2jmrkfmlkweq@localhost/hbrawdata'
    )
    
    engine = create_engine(database_url)
    
    print("Running migration: Add unique constraint on source_url")
    print("=" * 50)
    
    try:
        upgrade(engine)
        print("\n🎉 Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Attempting rollback...")
        try:
            downgrade(engine)
            print("✓ Rollback completed")
        except Exception as rollback_error:
            print(f"❌ Rollback failed: {rollback_error}")
        sys.exit(1)


if __name__ == "__main__":
    main()