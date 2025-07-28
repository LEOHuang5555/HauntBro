#!/usr/bin/env python3
"""
HauntBro Database Migration Runner
Safely executes the MVP schema cleanup migration
"""

import os
import sys
import psycopg2
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def load_env():
    """Load environment variables from .env file"""
    env_path = project_root / '.env'
    if not env_path.exists():
        print("❌ .env file not found. Please ensure .env exists in project root.")
        return None
    
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key] = value
    
    return env_vars

def get_db_connection(env_vars):
    """Create database connection using environment variables"""
    try:
        conn = psycopg2.connect(
            host=env_vars.get('DB_HOST', 'localhost'),
            port=env_vars.get('DB_PORT', '5432'),
            database=env_vars.get('DB_NAME', 'hbrawdata'),
            user=env_vars.get('DB_USER', 'hbadmin'),
            password=env_vars.get('DB_PASSWORD')
        )
        conn.autocommit = False  # We want transaction control
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def check_bronze_stories_count(conn):
    """Check number of bronze stories before migration"""
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM bronze_stories;")
            count = cur.fetchone()[0]
            return count
    except Exception as e:
        print(f"⚠️  Could not check bronze_stories count: {e}")
        return 0

def execute_migration(conn, migration_file):
    """Execute the migration SQL file"""
    try:
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print(f"🚀 Executing migration: {migration_file.name}")
        
        with conn.cursor() as cur:
            # Execute the migration
            cur.execute(migration_sql)
            
        conn.commit()
        print("✅ Migration executed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        return False

def verify_migration(conn):
    """Verify migration was successful"""
    try:
        with conn.cursor() as cur:
            # Check if verification view exists and query it
            cur.execute("""
                SELECT table_name, record_count, status 
                FROM mvp_schema_verification 
                ORDER BY table_name;
            """)
            
            results = cur.fetchall()
            
            print("\n📊 Migration Verification:")
            print("=" * 50)
            for table_name, record_count, status in results:
                print(f"  {table_name}: {record_count} records - {status}")
            
            # Specifically check bronze_stories preservation
            cur.execute("SELECT COUNT(*) FROM bronze_stories;")
            bronze_count = cur.fetchone()[0]
            
            print("=" * 50)
            print(f"🛡️  Bronze Stories Protected: {bronze_count} records preserved")
            
            return True
            
    except Exception as e:
        print(f"⚠️  Verification failed: {e}")
        return False

def main():
    """Main migration execution"""
    print("🏗️  HauntBro MVP Database Migration")
    print("=" * 50)
    
    # Load environment
    print("📋 Loading environment configuration...")
    env_vars = load_env()
    if not env_vars:
        sys.exit(1)
    
    # Connect to database
    print("🔌 Connecting to database...")
    conn = get_db_connection(env_vars)
    if not conn:
        sys.exit(1)
    
    try:
        # Check initial state
        print("🔍 Checking current database state...")
        initial_bronze_count = check_bronze_stories_count(conn)
        print(f"   Bronze stories before migration: {initial_bronze_count}")
        
        # Confirm migration
        migration_file = project_root / 'infrastructure' / 'database' / 'migrations' / '002_mvp_schema_cleanup.sql'
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            sys.exit(1)
        
        print(f"\n⚠️  About to execute migration: {migration_file.name}")
        print("   This will:")
        print("   ✅ Preserve ALL bronze_stories data")
        print("   🔄 Update silver_story_chunks to MVP schema")
        print("   🧹 Simplify user analytics tables")
        print("   💾 Backup existing complex tables")
        
        confirm = input("\n❓ Continue with migration? (yes/no): ").lower().strip()
        
        if confirm != 'yes':
            print("❌ Migration cancelled by user")
            sys.exit(0)
        
        # Execute migration
        print(f"\n⏳ Starting migration at {datetime.now()}")
        success = execute_migration(conn, migration_file)
        
        if not success:
            sys.exit(1)
        
        # Verify results
        print("\n🔍 Verifying migration results...")
        verify_migration(conn)
        
        # Final status
        final_bronze_count = check_bronze_stories_count(conn)
        
        if final_bronze_count == initial_bronze_count:
            print(f"\n✅ Migration completed successfully!")
            print(f"   ✅ Bronze stories preserved: {final_bronze_count}/{initial_bronze_count}")
            print(f"   ✅ MVP schema implemented")
            print(f"   ✅ Backup tables created")
        else:
            print(f"\n⚠️  Migration completed with warning:")
            print(f"   Bronze story count changed: {initial_bronze_count} → {final_bronze_count}")
        
    except KeyboardInterrupt:
        print("\n❌ Migration interrupted by user")
        conn.rollback()
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        conn.rollback()
        sys.exit(1)
    
    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()