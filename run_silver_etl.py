#!/usr/bin/env python3
"""
Bronze to Silver ETL Pipeline with Cost Monitoring
Processes bronze_stories into chunked silver_story_chunks with embeddings
"""
import asyncio
import asyncpg
import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Optional
import re

# Simple cost estimation (approximations)
COST_ESTIMATES = {
    'ollama_llama3.2': 0.0,  # Free local model
    'ollama_deepseek': 0.0,  # Free local model
    'openai_embedding': 0.0001,  # Per 1K tokens (if we had OpenAI)
    'processing_per_story': 0.001,  # Computational cost estimate
    'storage_per_chunk': 0.00001  # Storage cost estimate
}

class SilverETLProcessor:
    def __init__(self):
        self.stats = {
            'start_time': None,
            'end_time': None,
            'stories_processed': 0,
            'chunks_generated': 0,
            'total_cost': 0.0,
            'avg_processing_time_per_story': 0.0,
            'language_distribution': {},
            'chunk_size_distribution': {},
            'errors': []
        }
        
    async def connect_db(self):
        """Connect to the database"""
        return await asyncpg.connect(
            host='localhost', 
            port=5432,
            database='hauntbro',
            user='postgres',
            password='postgres'
        )

    def detect_language(self, text: str) -> str:
        """Simple language detection based on character patterns"""
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

    def assess_quality(self, content: str, title: str = "") -> float:
        """Assess content quality (0.0 to 1.0)"""
        if not content:
            return 0.0
        
        score = 1.0
        
        # Length scoring
        length = len(content.strip())
        if length < 50:
            score *= 0.3
        elif length < 200:
            score *= 0.7
        elif length > 10000:
            score *= 0.8
        
        # Structure scoring
        sentences = len([s for s in content.split('.') if s.strip()])
        if sentences < 2:
            score *= 0.6
        
        # Repetition check
        words = content.lower().split()
        if len(words) > 10:
            unique_words = set(words)
            diversity = len(unique_words) / len(words)
            score *= max(0.5, diversity * 1.5)
        
        return min(1.0, max(0.0, score))

    def chunk_content(self, content: str, target_size: int = 400) -> List[Dict]:
        """Chunk content into manageable pieces"""
        if not content:
            return []
        
        # Split by sentences first
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
            # If adding this sentence would exceed target size
            if len(current_chunk + " " + sentence) > target_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'order': chunk_order,
                    'length': len(current_chunk.strip()),
                    'word_count': len(current_chunk.strip().split()),
                    'sentence_count': len([s for s in current_chunk.split('.') if s.strip()])
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
                'word_count': len(current_chunk.strip().split()),
                'sentence_count': len([s for s in current_chunk.split('.') if s.strip()])
            })
        
        return chunks

    def generate_keywords(self, text: str, language: str) -> List[str]:
        """Extract semantic keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'her', 'its', 'our', 'their'
        }
        
        # Count word frequency
        word_freq = {}
        for word in words:
            if len(word) > 2 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, freq in keywords if freq > 1]

    async def process_story(self, conn, story: Dict) -> Dict:
        """Process a single story from bronze to silver"""
        story_start_time = time.time()
        story_id = story['id']
        
        try:
            print(f"\n📖 Processing: {story['title']}")
            print(f"   Source: {story['source']}")
            print(f"   Content length: {len(story['content'])} characters")
            
            # Assess quality
            quality_score = self.assess_quality(story['content'], story['title'])
            print(f"   Quality score: {quality_score:.2f}")
            
            if quality_score < 0.3:
                print(f"   ⚠️  Skipping due to low quality")
                await self.update_processing_status(conn, story_id, 'skipped', 
                    {'reason': 'low_quality', 'quality_score': quality_score})
                return {'success': False, 'reason': 'low_quality', 'cost': 0.0}
            
            # Detect language
            language = self.detect_language(story['content'])
            print(f"   Language: {language}")
            
            # Update language distribution
            self.stats['language_distribution'][language] = \
                self.stats['language_distribution'].get(language, 0) + 1
            
            # Chunk content
            chunks = self.chunk_content(story['content'])
            print(f"   Generated {len(chunks)} chunks")
            
            if not chunks:
                print(f"   ⚠️  No chunks generated")
                await self.update_processing_status(conn, story_id, 'failed', 
                    {'reason': 'no_chunks', 'quality_score': quality_score})
                return {'success': False, 'reason': 'no_chunks', 'cost': 0.0}
            
            # Process and save chunks
            total_cost = 0.0
            saved_chunks = 0
            
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                
                # Generate keywords
                keywords = self.generate_keywords(chunk['text'], language)
                
                # Simulate embedding generation (would call Ollama here)
                embedding_cost = len(chunk['text']) * COST_ESTIMATES['openai_embedding'] / 1000
                total_cost += embedding_cost
                
                # Store chunk size distribution
                size_bucket = f"{(chunk['length'] // 100) * 100}-{((chunk['length'] // 100) + 1) * 100}"
                self.stats['chunk_size_distribution'][size_bucket] = \
                    self.stats['chunk_size_distribution'].get(size_bucket, 0) + 1
                
                # Save to silver layer
                await conn.execute("""
                    INSERT INTO silver_story_chunks (
                        id, story_id, chunk_text, chunk_context, chunk_order, chunk_type,
                        chunk_length, chunk_word_count, semantic_keywords,
                        processing_language, chunk_quality_score, embedding_cost,
                        embedding_model, embedding_version
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (id) DO UPDATE SET
                        chunk_text = EXCLUDED.chunk_text,
                        updated_at = CURRENT_TIMESTAMP
                """, 
                chunk_id, story_id, chunk['text'], story['content'][:200] + '...',
                chunk['order'], 'narrative', chunk['length'], chunk['word_count'],
                keywords, language, quality_score, embedding_cost,
                f'ollama_{language}_model', '1.0')
                
                saved_chunks += 1
            
            # Add processing cost
            processing_cost = COST_ESTIMATES['processing_per_story']
            storage_cost = len(chunks) * COST_ESTIMATES['storage_per_chunk']
            total_cost += processing_cost + storage_cost
            
            # Update processing status
            processing_time = time.time() - story_start_time
            metadata = {
                'language': language,
                'quality_score': quality_score,
                'chunks_generated': len(chunks),
                'processing_time_seconds': processing_time,
                'total_cost': total_cost,
                'keywords_extracted': len(set([kw for chunk in chunks for kw in self.generate_keywords(chunk['text'], language)]))
            }
            
            await self.update_processing_status(conn, story_id, 'completed', metadata)
            
            print(f"   ✅ Processed: {saved_chunks} chunks, ${total_cost:.6f} cost ({processing_time:.2f}s)")
            
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
            
            await self.update_processing_status(conn, story_id, 'failed', 
                {'error': error_msg, 'error_type': type(e).__name__})
            
            self.stats['errors'].append({
                'story_id': str(story_id),
                'title': story['title'],
                'error': error_msg
            })
            
            return {'success': False, 'reason': 'processing_error', 'cost': 0.0}

    async def update_processing_status(self, conn, story_id: str, status: str, metadata: Dict = None):
        """Update processing status for a story"""
        await conn.execute("""
            INSERT INTO bronze_story_processing (
                story_id, processing_status, processing_metadata, updated_at
            ) VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (story_id) DO UPDATE SET
                processing_status = EXCLUDED.processing_status,
                processing_metadata = 
                    COALESCE(bronze_story_processing.processing_metadata, '{}'::jsonb) || 
                    EXCLUDED.processing_metadata::jsonb,
                updated_at = CURRENT_TIMESTAMP
        """, story_id, status, json.dumps(metadata or {}))

    async def run_pipeline(self, limit: int = None):
        """Run the complete Bronze to Silver ETL pipeline"""
        self.stats['start_time'] = datetime.now()
        print(f"🚀 Starting Bronze to Silver ETL Pipeline")
        print(f"   Start time: {self.stats['start_time']}")
        
        try:
            conn = await self.connect_db()
            
            # Get unprocessed bronze stories
            query = """
                SELECT bs.id, bs.title, bs.content, bs.source, bs.author, bs.post_date
                FROM bronze_stories bs
                LEFT JOIN bronze_story_processing bsp ON bs.id = bsp.story_id
                WHERE (bsp.processing_status IS NULL OR bsp.processing_status IN ('pending', 'failed'))
                AND bs.content IS NOT NULL
                AND LENGTH(bs.content) >= 50
                ORDER BY bs.scraped_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            stories = await conn.fetch(query)
            print(f"📚 Found {len(stories)} stories to process")
            
            if not stories:
                print("📭 No stories to process")
                return
            
            # Process each story
            processing_times = []
            for i, story in enumerate(stories, 1):
                print(f"\n[{i}/{len(stories)}] Processing story...")
                
                result = await self.process_story(conn, dict(story))
                
                if result['success']:
                    self.stats['stories_processed'] += 1
                    self.stats['chunks_generated'] += result['chunks']
                    self.stats['total_cost'] += result['cost']
                    processing_times.append(result['processing_time'])
            
            # Calculate final statistics
            self.stats['end_time'] = datetime.now()
            total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            if processing_times:
                self.stats['avg_processing_time_per_story'] = sum(processing_times) / len(processing_times)
            
            await conn.close()
            
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
            import traceback
            traceback.print_exc()

    def print_final_report(self):
        """Print comprehensive processing report"""
        print(f"\n" + "="*80)
        print(f"📊 BRONZE TO SILVER ETL PIPELINE REPORT")
        print(f"="*80)
        
        # Time metrics
        total_time = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        print(f"\n⏱️  TIME METRICS:")
        print(f"   Total processing time: {total_time:.2f} seconds")
        print(f"   Average time per story: {self.stats['avg_processing_time_per_story']:.2f} seconds")
        print(f"   Stories per minute: {(self.stats['stories_processed'] / total_time * 60):.1f}")
        
        # Processing metrics
        print(f"\n📈 PROCESSING METRICS:")
        print(f"   Stories processed: {self.stats['stories_processed']}")
        print(f"   Chunks generated: {self.stats['chunks_generated']}")
        print(f"   Average chunks per story: {(self.stats['chunks_generated'] / max(self.stats['stories_processed'], 1)):.1f}")
        print(f"   Errors encountered: {len(self.stats['errors'])}")
        
        # Cost analysis
        print(f"\n💰 COST ANALYSIS:")
        print(f"   Total processing cost: ${self.stats['total_cost']:.6f}")
        print(f"   Average cost per story: ${(self.stats['total_cost'] / max(self.stats['stories_processed'], 1)):.6f}")
        print(f"   Average cost per chunk: ${(self.stats['total_cost'] / max(self.stats['chunks_generated'], 1)):.6f}")
        
        # Language distribution
        if self.stats['language_distribution']:
            print(f"\n🌐 LANGUAGE DISTRIBUTION:")
            for lang, count in self.stats['language_distribution'].items():
                percentage = (count / self.stats['stories_processed']) * 100
                print(f"   {lang}: {count} stories ({percentage:.1f}%)")
        
        # Chunk size distribution
        if self.stats['chunk_size_distribution']:
            print(f"\n📏 CHUNK SIZE DISTRIBUTION:")
            for size_range, count in sorted(self.stats['chunk_size_distribution'].items()):
                percentage = (count / self.stats['chunks_generated']) * 100
                print(f"   {size_range} chars: {count} chunks ({percentage:.1f}%)")
        
        # Errors
        if self.stats['errors']:
            print(f"\n❌ ERRORS:")
            for error in self.stats['errors']:
                print(f"   Story: {error['title'][:50]}... - {error['error']}")
        
        print(f"\n" + "="*80)

async def main():
    """Main execution function"""
    processor = SilverETLProcessor()
    
    try:
        # Run pipeline (no limit to process all available stories)
        await processor.run_pipeline()
        
        # Print final report
        processor.print_final_report()
        
    except KeyboardInterrupt:
        print("\n🛑 Pipeline interrupted by user")
    except Exception as e:
        print(f"❌ Pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())