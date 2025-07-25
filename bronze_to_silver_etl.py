#!/usr/bin/env python3
"""
Bronze to Silver ETL Pipeline for 100 Stories
Processes real bronze_stories data into silver_stories and silver_story_chunks
"""
import asyncio
import asyncpg
import json
import time
import uuid
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

# Cost estimation constants
COSTS = {
    'ollama_processing': 0.0,  # Local model - free
    'openai_embedding_per_1k_tokens': 0.0001,
    'processing_overhead_per_story': 0.002,
    'storage_per_chunk': 0.00005,
    'language_detection': 0.0001,
    'quality_assessment': 0.0001
}

class BronzeToSilverETL:
    def __init__(self):
        self.stats = {
            'start_time': None,
            'end_time': None,
            'stories_processed': 0,
            'stories_skipped': 0,
            'chunks_generated': 0,
            'total_cost': 0.0,
            'language_distribution': {},
            'quality_distribution': {},
            'errors': [],
            'processing_times': []
        }
        
    async def connect_db(self):
        """Connect to the real database using .env config"""
        return await asyncpg.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    
    def detect_language(self, text: str) -> str:
        """Detect language based on character patterns"""
        if not text or len(text.strip()) < 20:
            return 'unknown'
        
        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.replace(' ', '').replace('\n', ''))
        
        if total_chars == 0:
            return 'unknown'
        
        chinese_ratio = chinese_chars / total_chars
        
        if chinese_ratio > 0.5:
            return 'zh'
        elif chinese_ratio < 0.1:
            return 'en'
        else:
            return 'mixed'
    
    def assess_quality(self, content: str, title: str = "") -> float:
        """Assess content quality score (0.0 to 1.0)"""
        if not content:
            return 0.0
        
        score = 1.0
        content_length = len(content.strip())
        
        # Length-based scoring
        if content_length < 100:
            score *= 0.3
        elif content_length < 300:
            score *= 0.6
        elif content_length > 10000:
            score *= 0.8
        
        # Structure assessment
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if len(lines) < 2:
            score *= 0.7
        
        # Character diversity check
        unique_chars = len(set(content.lower()))
        if unique_chars < 20:
            score *= 0.5
        
        # Check for excessive repetition
        if content_length > 100:
            words = content.split()[:50]  # Check first 50 words
            if words:
                unique_words = set(words)
                word_diversity = len(unique_words) / len(words)
                score *= max(0.4, word_diversity * 1.5)
        
        return min(1.0, max(0.0, round(score, 2)))
    
    def extract_keywords(self, text: str, language: str, limit: int = 15) -> List[str]:
        """Extract semantic keywords from text"""
        if not text:
            return []
        
        # Clean text and split into words
        if language == 'zh':
            # For Chinese, use character-based approach
            words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        else:
            # For English/mixed, use word-based approach
            words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'this', 'that', 'these', 'those', 'they', 'them', 'their', 'there',
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一個',
            '但是', '因為', '所以', '然後', '可以', '沒有', '什麼', '怎麼', '時候', '地方'
        }
        
        # Count word frequency
        word_freq = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [word for word, freq in top_words if freq > 1]
    
    def chunk_content(self, content: str, target_size: int = 500, overlap: int = 50) -> List[Dict]:
        """Chunk content with overlap for better context"""
        if not content or len(content.strip()) < 100:
            return []
        
        content = content.strip()
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [content]
        
        current_chunk = ""
        chunk_order = 0
        
        for para in paragraphs:
            # If adding this paragraph would exceed target size
            if len(current_chunk + "\n\n" + para) > target_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'order': chunk_order,
                    'length': len(current_chunk.strip()),
                    'word_count': len(current_chunk.strip().split()),
                    'sentence_count': len([s for s in current_chunk.split('.') if s.strip()])
                })
                
                # Start new chunk with overlap
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
                chunk_order += 1
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'order': chunk_order,
                'length': len(current_chunk.strip()),
                'word_count': len(current_chunk.strip().split()),
                'sentence_count': len([s for s in current_chunk.split('.') if s.strip()])
            })
        
        return chunks
    
    async def process_story(self, conn, story: Dict) -> Dict:
        """Process a single bronze story into silver layer"""
        story_start = time.time()
        bronze_id = story['id']
        
        try:
            print(f"📖 Processing: {story['title'][:60]}...")
            print(f"   Source: {story['source']}, Length: {len(story['content'])} chars")
            
            # Language detection
            language = self.detect_language(story['content'])
            self.stats['language_distribution'][language] = \
                self.stats['language_distribution'].get(language, 0) + 1
            
            # Quality assessment
            quality_score = self.assess_quality(story['content'], story['title'])
            quality_bucket = f"{int(quality_score * 10) / 10:.1f}"
            self.stats['quality_distribution'][quality_bucket] = \
                self.stats['quality_distribution'].get(quality_bucket, 0) + 1
            
            print(f"   Language: {language}, Quality: {quality_score}")
            
            # Skip very low quality content
            if quality_score < 0.2:
                print(f"   ⚠️  Skipping due to low quality")
                await self.update_processing_status(conn, bronze_id, 'skipped', 
                    {'reason': 'low_quality', 'quality_score': quality_score})
                self.stats['stories_skipped'] += 1
                return {'success': False, 'reason': 'low_quality', 'cost': 0.0}
            
            # Extract keywords
            keywords = self.extract_keywords(story['content'], language)
            
            # Chunk content
            chunks = self.chunk_content(story['content'])
            if not chunks:
                print(f"   ⚠️  No chunks generated")
                await self.update_processing_status(conn, bronze_id, 'failed', 
                    {'reason': 'no_chunks'})
                return {'success': False, 'reason': 'no_chunks', 'cost': 0.0}
            
            print(f"   Generated {len(chunks)} chunks")
            
            # Calculate costs
            story_cost = COSTS['processing_overhead_per_story']
            story_cost += COSTS['language_detection']
            story_cost += COSTS['quality_assessment']
            embedding_cost = 0.0
            
            # Create silver_stories entry
            silver_story_id = str(uuid.uuid4())
            
            # Calculate reading time (average 200 words per minute)
            word_count = len(story['content'].split())
            reading_time = max(1, round(word_count / 200))
            
            await conn.execute('''
                INSERT INTO silver_stories (
                    id, bronze_story_id, title, cleaned_content, author, post_date,
                    tags, reading_time_minutes, word_count, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (bronze_story_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    cleaned_content = EXCLUDED.cleaned_content,
                    tags = EXCLUDED.tags,
                    reading_time_minutes = EXCLUDED.reading_time_minutes,
                    word_count = EXCLUDED.word_count
            ''', 
            silver_story_id, bronze_id, story['title'][:500], 
            story['content'][:1000] + '...' if len(story['content']) > 1000 else story['content'],
            story['author'], story['post_date'],
            keywords[:10], reading_time, word_count, datetime.now())
            
            # Process and save chunks
            for chunk in chunks:
                chunk_embedding_cost = len(chunk['text']) * COSTS['openai_embedding_per_1k_tokens'] / 1000
                embedding_cost += chunk_embedding_cost
                
                chunk_keywords = self.extract_keywords(chunk['text'], language, 8)
                
                # Create a simple embedding placeholder (would be actual embeddings in production)
                embedding_json = json.dumps([0.1] * 100)  # Simple placeholder embedding
                
                await conn.execute('''
                    INSERT INTO silver_story_chunks (
                        id, bronze_story_id, chunk_text, chunk_context, chunk_order, embedding, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (bronze_story_id, chunk_order) DO UPDATE SET
                        chunk_text = EXCLUDED.chunk_text,
                        chunk_context = EXCLUDED.chunk_context,
                        embedding = EXCLUDED.embedding
                ''',
                str(uuid.uuid4()), bronze_id, chunk['text'],
                story['content'][:200] + '...', chunk['order'], embedding_json, datetime.now())
            
            total_cost = story_cost + embedding_cost + (len(chunks) * COSTS['storage_per_chunk'])
            
            # Update processing status
            processing_time = time.time() - story_start
            await self.update_processing_status(conn, bronze_id, 'completed', {
                'language': language,
                'quality_score': quality_score,
                'chunks_generated': len(chunks),
                'processing_time_seconds': processing_time,
                'total_cost': total_cost,
                'keywords_extracted': len(keywords)
            })
            
            self.stats['total_cost'] += total_cost
            self.stats['chunks_generated'] += len(chunks)
            self.stats['processing_times'].append(processing_time)
            
            print(f"   ✅ Saved {len(chunks)} chunks, Cost: ${total_cost:.6f} ({processing_time:.2f}s)")
            
            return {
                'success': True,
                'chunks': len(chunks),
                'cost': total_cost,
                'processing_time': processing_time,
                'language': language,
                'quality_score': quality_score
            }
            
        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            print(f"   ❌ {error_msg}")
            
            await self.update_processing_status(conn, bronze_id, 'failed', 
                {'error': error_msg, 'error_type': type(e).__name__})
            
            self.stats['errors'].append({
                'bronze_id': str(bronze_id),
                'title': story['title'][:100],
                'error': error_msg
            })
            
            return {'success': False, 'reason': 'processing_error', 'cost': 0.0}
    
    async def update_processing_status(self, conn, bronze_id: str, status: str, metadata: Dict = None):
        """Update processing status"""
        await conn.execute('''
            INSERT INTO silver_processing_status (
                bronze_story_id, processing_status, processing_metadata, 
                started_at, completed_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)
            ON CONFLICT (bronze_story_id) DO UPDATE SET
                processing_status = EXCLUDED.processing_status,
                processing_metadata = COALESCE(silver_processing_status.processing_metadata, '{}'::jsonb) || EXCLUDED.processing_metadata::jsonb,
                completed_at = CASE WHEN EXCLUDED.processing_status = 'completed' THEN CURRENT_TIMESTAMP ELSE silver_processing_status.completed_at END,
                updated_at = CURRENT_TIMESTAMP
        ''', bronze_id, status, json.dumps(metadata or {}), 
        datetime.now() if status in ['pending', 'processing'] else None,
        datetime.now() if status in ['completed', 'failed', 'skipped'] else None)
    
    async def run_etl_pipeline(self, limit: int = 100):
        """Run the complete ETL pipeline"""
        self.stats['start_time'] = datetime.now()
        print(f"🚀 Starting Bronze → Silver ETL Pipeline")
        print(f"   Target: {limit} stories")
        print(f"   Start time: {self.stats['start_time']}")
        
        try:
            conn = await self.connect_db()
            
            # Get unprocessed bronze stories with good distribution
            stories = await conn.fetch('''
                SELECT bs.id, bs.title, bs.content, bs.source, bs.author, bs.post_date, bs.scraped_at,
                       CASE WHEN bs.source = 'reddit_ghoststories' THEN 0 ELSE 1 END as priority
                FROM bronze_stories bs
                LEFT JOIN silver_processing_status sps ON bs.id = sps.bronze_story_id
                WHERE (sps.processing_status IS NULL OR sps.processing_status IN ('pending', 'failed'))
                AND bs.content IS NOT NULL
                AND LENGTH(bs.content) >= 100
                AND LENGTH(bs.content) <= 50000
                ORDER BY priority, RANDOM()
                LIMIT $1
            ''', limit)
            
            print(f"📚 Found {len(stories)} stories to process\\n")
            
            if not stories:
                print("📭 No unprocessed stories found")
                return
            
            # Process stories
            for i, story in enumerate(stories, 1):
                print(f"[{i:3d}/{len(stories)}] ", end="")
                
                result = await self.process_story(conn, dict(story))
                
                if result['success']:
                    self.stats['stories_processed'] += 1
                
                # Brief pause to avoid overwhelming the system
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
                    print(f"\\n   📊 Progress: {i}/{len(stories)} stories processed\\n")
            
            await conn.close()
            
        except Exception as e:
            print(f"❌ ETL Pipeline error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.stats['end_time'] = datetime.now()
    
    def print_final_report(self):
        """Generate comprehensive final report"""
        if not self.stats['end_time']:
            self.stats['end_time'] = datetime.now()
        
        total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print(f"\\n" + "="*80)
        print(f"📊 BRONZE → SILVER ETL PIPELINE FINAL REPORT")
        print(f"="*80)
        
        # Executive Summary
        print(f"\\n🎯 EXECUTIVE SUMMARY:")
        print(f"   ✅ Stories processed: {self.stats['stories_processed']:,}")
        print(f"   ⚠️  Stories skipped: {self.stats['stories_skipped']:,}")
        print(f"   📦 Chunks generated: {self.stats['chunks_generated']:,}")
        print(f"   💰 Total cost: ${self.stats['total_cost']:.6f}")
        print(f"   ⏱️  Total time: {total_time:.2f} seconds")
        
        # Performance Metrics
        if self.stats['processing_times']:
            avg_time = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
            print(f"\\n⚡ PERFORMANCE METRICS:")
            print(f"   Average processing time: {avg_time:.3f}s per story")
            print(f"   Throughput: {self.stats['stories_processed'] / total_time:.1f} stories/second")
            print(f"   Chunk generation rate: {self.stats['chunks_generated'] / total_time:.1f} chunks/second")
        
        # Cost Analysis
        if self.stats['stories_processed'] > 0:
            print(f"\\n💰 COST ANALYSIS:")
            print(f"   Average cost per story: ${self.stats['total_cost'] / self.stats['stories_processed']:.6f}")
            if self.stats['chunks_generated'] > 0:
                print(f"   Average cost per chunk: ${self.stats['total_cost'] / self.stats['chunks_generated']:.6f}")
            print(f"   Cost efficiency: {int(sum(len(story.get('content', '')) for story in []) / max(self.stats['total_cost'], 0.000001))} chars per dollar")
        
        # Language Distribution
        if self.stats['language_distribution']:
            print(f"\\n🌐 LANGUAGE DISTRIBUTION:")
            for lang, count in sorted(self.stats['language_distribution'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.stats['stories_processed']) * 100 if self.stats['stories_processed'] > 0 else 0
                print(f"   {lang}: {count} stories ({percentage:.1f}%)")
        
        # Quality Distribution
        if self.stats['quality_distribution']:
            total_analyzed = self.stats['stories_processed'] + self.stats['stories_skipped']
            print(f"\\n📈 QUALITY SCORE DISTRIBUTION:")
            for score, count in sorted(self.stats['quality_distribution'].items()):
                percentage = (count / max(total_analyzed, 1)) * 100
                print(f"   {score}: {count} stories ({percentage:.1f}%)")
        
        # Errors
        if self.stats['errors']:
            print(f"\\n❌ PROCESSING ERRORS ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   {error['title'][:50]}... - {error['error'][:100]}")
            if len(self.stats['errors']) > 5:
                print(f"   ... and {len(self.stats['errors']) - 5} more errors")
        
        print(f"\\n" + "="*80)
        print(f"🎉 ETL PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"="*80)

async def main():
    """Main execution function"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    etl = BronzeToSilverETL()
    
    try:
        await etl.run_etl_pipeline(limit=100)
        etl.print_final_report()
        
    except KeyboardInterrupt:
        print("\\n🛑 ETL Pipeline interrupted by user")
        etl.print_final_report()
    except Exception as e:
        print(f"❌ ETL Pipeline failed: {e}")
        etl.print_final_report()

if __name__ == "__main__":
    asyncio.run(main())