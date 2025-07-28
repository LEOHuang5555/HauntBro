#!/usr/bin/env python3
"""
Simplified Bronze to Silver ETL Pipeline
Works with existing database tables and basic processing
"""
import asyncio
import os
import json
import uuid
import time
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleBronzeToSilverETL:
    """Simplified Bronze to Silver ETL Pipeline"""
    
    def __init__(self, test_mode: bool = False, limit: Optional[int] = None):
        self.test_mode = test_mode
        self.limit = limit if limit else (5 if test_mode else 50)
        
        self.stats = {
            'start_time': None,
            'end_time': None,
            'stories_processed': 0,
            'stories_skipped': 0,
            'stories_failed': 0,
            'chunks_generated': 0,
            'errors': []
        }
        
        print(f"🚀 Initializing Simplified Bronze→Silver ETL")
        print(f"   Test Mode: {'ON' if test_mode else 'OFF'}")
        print(f"   Limit: {self.limit}")

    async def get_database_connection(self):
        """Get database connection"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn_params = {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT')),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }
            
            conn = psycopg2.connect(**conn_params)
            conn.autocommit = True
            return conn
            
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None

    def detect_language(self, text: str) -> str:
        """Simple language detection"""
        if not text:
            return 'unknown'
        
        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            return 'unknown'
        
        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio > 0.3:
            return 'zh'
        elif chinese_ratio < 0.1:
            return 'en'
        else:
            return 'mixed'

    def assess_quality(self, content: str) -> float:
        """Assess content quality (0.0 to 1.0)"""
        if not content:
            return 0.0
        
        score = 1.0
        length = len(content.strip())
        
        # Length scoring
        if length < 100:
            score *= 0.3
        elif length < 300:
            score *= 0.7
        elif length > 20000:
            score *= 0.8
        
        # Structure scoring
        sentences = len([s for s in content.split('.') if s.strip()])
        if sentences < 2:
            score *= 0.6
        
        return min(1.0, max(0.0, score))

    def chunk_content(self, content: str, target_size: int = 500) -> List[Dict]:
        """Chunk content into manageable pieces"""
        if not content:
            return []
        
        # Split by sentences
        sentences = []
        for sent in re.split(r'[.!?]+', content):
            sent = sent.strip()
            if sent:
                sentences.append(sent + '.')
        
        if not sentences:
            return []
        
        chunks = []
        current_chunk = ""
        chunk_order = 0
        
        for sentence in sentences:
            if len(current_chunk + " " + sentence) > target_size and current_chunk:
                chunks.append({
                    'text': current_chunk.strip(),
                    'order': chunk_order,
                    'length': len(current_chunk.strip()),
                    'word_count': len(current_chunk.strip().split())
                })
                chunk_order += 1
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'order': chunk_order,
                'length': len(current_chunk.strip()),
                'word_count': len(current_chunk.strip().split())
            })
        
        return chunks

    async def get_unprocessed_stories(self, conn) -> List[Dict]:
        """Get bronze stories that haven't been processed to silver"""
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Get stories that don't have silver chunks yet
                query = """
                SELECT bs.id, bs.title, bs.content, bs.source, bs.author, bs.post_date
                FROM bronze_stories bs
                LEFT JOIN silver_story_chunks ssc ON bs.id = ssc.story_id
                WHERE ssc.story_id IS NULL 
                  AND LENGTH(bs.content) > 100
                ORDER BY bs.post_date DESC
                LIMIT %s
                """
                
                cur.execute(query, (self.limit,))
                stories = cur.fetchall()
                
                print(f"📚 Found {len(stories)} unprocessed stories")
                return [dict(story) for story in stories]
                
        except Exception as e:
            print(f"❌ Error fetching stories: {e}")
            return []

    async def save_silver_chunks(self, conn, story_id: str, chunks: List[Dict], language: str, quality_score: float, story: Dict):
        """Save chunks to silver_story_chunks table"""
        try:
            with conn.cursor() as cur:
                for chunk in chunks:
                    chunk_id = str(uuid.uuid4())
                    
                    # Insert into silver_story_chunks (matching actual schema)
                    insert_query = """
                    INSERT INTO silver_story_chunks (
                        id, story_id, chunk_text, chunk_context, chunk_order
                    ) VALUES (
                        %s, %s, %s, %s, %s
                    )
                    """
                    
                    # Create context from first 200 chars of story content
                    context = story.get('content', '')[:200] + '...' if len(story.get('content', '')) > 200 else story.get('content', '')
                    
                    cur.execute(insert_query, (
                        chunk_id,
                        story_id,
                        chunk['text'],
                        context,
                        chunk['order']
                    ))
                
                return True
                
        except Exception as e:
            print(f"❌ Error saving chunks: {e}")
            return False

    async def process_story(self, conn, story: Dict) -> Dict:
        """Process a single story"""
        story_id = str(story['id'])
        title = story.get('title', 'Untitled')[:50]
        
        try:
            print(f"\n📖 Processing: {title}")
            print(f"   Story ID: {story_id}")
            print(f"   Content Length: {len(story.get('content', ''))} chars")
            
            # Assess quality
            quality_score = self.assess_quality(story['content'])
            print(f"   Quality Score: {quality_score:.2f}")
            
            if quality_score < 0.3:
                print(f"   ⚠️  Skipped: Low quality score")
                self.stats['stories_skipped'] += 1
                return {'status': 'skipped', 'reason': 'low_quality'}
            
            # Detect language
            language = self.detect_language(story['content'])
            print(f"   Language: {language}")
            
            # Chunk content
            chunks = self.chunk_content(story['content'])
            print(f"   Generated: {len(chunks)} chunks")
            
            if not chunks:
                print(f"   ⚠️  Skipped: No chunks generated")
                self.stats['stories_skipped'] += 1
                return {'status': 'skipped', 'reason': 'no_chunks'}
            
            # Save to silver layer
            if await self.save_silver_chunks(conn, story_id, chunks, language, quality_score, story):
                print(f"   ✅ Success: Saved {len(chunks)} chunks")
                self.stats['stories_processed'] += 1
                self.stats['chunks_generated'] += len(chunks)
                return {
                    'status': 'success',
                    'chunks': len(chunks),
                    'language': language,
                    'quality_score': quality_score
                }
            else:
                print(f"   ❌ Failed: Could not save chunks")
                self.stats['stories_failed'] += 1
                return {'status': 'failed', 'reason': 'save_error'}
                
        except Exception as e:
            error_msg = f"Error processing story {story_id}: {str(e)}"
            print(f"   ❌ {error_msg}")
            self.stats['stories_failed'] += 1
            self.stats['errors'].append({'story_id': story_id, 'title': title, 'error': error_msg})
            return {'status': 'failed', 'reason': 'processing_error'}

    async def run_pipeline(self):
        """Run the complete pipeline"""
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        print(f"\n{'='*60}")
        print(f"🚀 STARTING SIMPLIFIED BRONZE→SILVER ETL PIPELINE")
        print(f"{'='*60}")
        
        # Get database connection
        conn = await self.get_database_connection()
        if not conn:
            print("❌ Could not establish database connection")
            return False
        
        try:
            # Get unprocessed stories
            stories = await self.get_unprocessed_stories(conn)
            
            if not stories:
                print("📭 No unprocessed stories found")
                return True
            
            # Process stories
            print(f"\n⚙️  Processing {len(stories)} stories...")
            
            for i, story in enumerate(stories, 1):
                print(f"\n[{i}/{len(stories)}]", end="")
                result = await self.process_story(conn, story)
                
                # Brief delay between stories
                await asyncio.sleep(0.5)
            
            self.stats['end_time'] = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            return False
        finally:
            conn.close()

    def print_report(self):
        """Print final processing report"""
        if not self.stats['start_time'] or not self.stats['end_time']:
            print("❌ Pipeline did not complete")
            return
        
        total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"📊 SIMPLIFIED BRONZE→SILVER ETL REPORT")
        print(f"{'='*60}")
        print(f"Duration: {total_time:.2f} seconds")
        print(f"Stories Processed: {self.stats['stories_processed']}")
        print(f"Stories Skipped: {self.stats['stories_skipped']}")
        print(f"Stories Failed: {self.stats['stories_failed']}")
        print(f"Chunks Generated: {self.stats['chunks_generated']}")
        
        if self.stats['stories_processed'] > 0:
            avg_chunks = self.stats['chunks_generated'] / self.stats['stories_processed']
            print(f"Average Chunks per Story: {avg_chunks:.1f}")
        
        if self.stats['errors']:
            print(f"\nErrors:")
            for error in self.stats['errors'][-3:]:
                print(f"  • {error['title']}: {error['error'][:50]}...")
        
        print(f"{'='*60}")

async def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simplified Bronze to Silver ETL")
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode')
    parser.add_argument('--limit', type=int, help='Limit number of stories')
    
    args = parser.parse_args()
    
    etl = SimpleBronzeToSilverETL(test_mode=args.test_mode, limit=args.limit)
    
    try:
        success = await etl.run_pipeline()
        etl.print_report()
        
        if success:
            print("\n🎉 ETL pipeline completed!")
        else:
            print("\n❌ ETL pipeline failed")
            
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    # Make sure we have psycopg2
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("❌ psycopg2 not installed. Install with: pip install psycopg2-binary")
        exit(1)
    
    asyncio.run(main())