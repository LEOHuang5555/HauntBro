#!/usr/bin/env python3
"""
Fix database constraint to allow reddit_nosleep source.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_source_constraint():
    """Update the valid_source constraint to include reddit_nosleep."""
    
    # Get database URL
    db_url = os.getenv('DATABASE_URL', 'postgresql+psycopg2://hbadmin:dj3jkp2jmrkfmlkweq@localhost/hbrawdata')
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            print("Connected to database")
            
            # Drop old constraint
            print("Dropping old constraint...")
            conn.execute(text("ALTER TABLE bronze_stories DROP CONSTRAINT IF EXISTS valid_source;"))
            
            # Add new constraint with reddit_nosleep
            print("Adding new constraint...")
            conn.execute(text("""
                ALTER TABLE bronze_stories 
                ADD CONSTRAINT valid_source 
                CHECK (source IN ('ptt_marvel', 'reddit_ghoststories', 'reddit_nosleep'));
            """))
            
            conn.commit()
            print("✅ Constraint updated successfully!")
            
            # Verify the constraint
            result = conn.execute(text("""
                SELECT conname, consrc 
                FROM pg_constraint 
                WHERE conname = 'valid_source' AND conrelid = 'bronze_stories'::regclass;
            """))
            
            for row in result:
                print(f"Constraint: {row[0]} - {row[1]}")
                
        return True
        
    except Exception as e:
        print(f"❌ Error updating constraint: {e}")
        return False

if __name__ == "__main__":
    success = fix_source_constraint()
    sys.exit(0 if success else 1)