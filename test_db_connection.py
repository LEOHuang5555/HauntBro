#!/usr/bin/env python3
"""
Simple database connection test
"""
import os
import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_database_connection():
    """Test basic database connectivity"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Get connection parameters from environment
        conn_params = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        print(f"🔍 Testing connection to {conn_params['host']}:{conn_params['port']}/{conn_params['database']}")
        
        # Test connection
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True  # Avoid transaction issues
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Test basic query
            cur.execute("SELECT version()")
            version = cur.fetchone()['version']
            print(f"✅ Database connected successfully")
            print(f"   PostgreSQL version: {version.split()[1] if version else 'unknown'}")
            
            # Check medallion tables
            tables = ['bronze_stories', 'silver_story_chunks', 'gold_layer_metrics']
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                    count = cur.fetchone()['count']
                    print(f"   Table {table}: {count} records")
                except psycopg2.Error as e:
                    print(f"   Table {table}: ❌ {e}")
        
        conn.close()
        return True
        
    except ImportError:
        print("❌ psycopg2 not installed")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_ollama_connection():
    """Test Ollama service connectivity"""
    try:
        import requests
        
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        print(f"🔍 Testing Ollama at {ollama_url}")
        
        response = requests.get(f"{ollama_url}/api/tags", timeout=10)
        response.raise_for_status()
        
        models_data = response.json()
        models = models_data.get('models', [])
        model_names = [model['name'] for model in models]
        
        print(f"✅ Ollama connected successfully")
        print(f"   Available models: {len(models)}")
        for model in model_names[:5]:  # Show first 5 models
            print(f"   - {model}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 HauntBro Database & Ollama Connection Test")
    print("=" * 50)
    
    db_ok = test_database_connection()
    print()
    ollama_ok = test_ollama_connection()
    
    print()
    print("=" * 50)
    if db_ok and ollama_ok:
        print("✅ All connections successful - ready for ETL pipeline")
        sys.exit(0)
    else:
        print("❌ Some connections failed - check configuration")
        sys.exit(1)