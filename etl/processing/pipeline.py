import asyncio
from typing import List, Dict
from datetime import datetime
from dataclasses import asdict

from chunking import StoryChunker, ChunkConfig, StoryChunk
from embedding import EmbeddingGenerator
from database import DatabaseManager
from quality_score import assess_content_quality
from etl.config.config import CONFIG

class ChunkingPipeline:
    """Main orchestrator for the story chunking pipeline"""
    
    def __init__(self):
        self.chunker = StoryChunker()
        self.embedding_generator = EmbeddingGenerator(use_openai=True)
        self.db_manager = DatabaseManager()
        self.stats = {
            'processed': 0,
            'failed': 0,
            'total_chunks': 0,
            'start_time': None,
            'errors': []
        }
    
    async def initialize(self):
        """Initialize all components"""
        print("🚀 Initializing chunking pipeline...")
        
        # Connect to database
        db_connected = await self.db_manager.connect()
        if not db_connected:
            raise Exception("Failed to connect to database")
        
        # Test embedding service
        try:
            test_emb = await self.embedding_generator.generate_embeddings_async(
                "test text", "test context"
            )
            if not test_emb[0]:  # If empty embeddings
                raise Exception("Embedding service test failed")
            print("✅ Embedding service ready")
        except Exception as e:
            print(f"❌ Embedding service failed: {e}")
            raise
        
        print("✅ Pipeline initialized successfully")
        return True
    
    async def process_single_story(self, story_data: Dict) -> bool:
        """Process a single story through the complete pipeline"""
        story_id = story_data['id']
        content = story_data['content']
        title = story_data.get('title', 'Untitled')
        
        try:
            print(f"📖 Processing: {title[:50]}...")
            
            # Update status to processing
            await self.db_manager.update_story_processing_status(
                story_id, 
                'processing',
                {'start_time': datetime.utcnow().isoformat()}
            )
            
            # Check content quality
            quality_score = assess_content_quality(content)
            if quality_score < CONFIG["chunking"].min_quality_score:
                print(f"⚠️  Low quality content (score: {quality_score}), skipping...")
                await self.db_manager.update_story_processing_status(
                    story_id, 
                    'skipped_low_quality',
                    {'quality_score': quality_score}
                )
                return False
            
            # Generate chunks using LLM
            story_chunks = await self.chunker.chunk_story(story_id, content, title)
            
            if not story_chunks:
                print("❌ No chunks generated")
                await self.db_manager.update_story_processing_status(story_id, 'failed_no_chunks')
                self.stats['failed'] += 1
                return False
            
            # Convert StoryChunk objects to database format
            chunk_dicts = []
            for chunk in story_chunks:
                # Generate embeddings if not already done
                if not chunk.content_embedding:
                    content_emb, search_emb = await self.embedding_generator.generate_embeddings_async(
                        chunk.chunk_text, chunk.chunk_context
                    )
                    chunk.content_embedding = content_emb
                    chunk.search_embedding = search_emb
                
                # Convert to dict for database
                chunk_dict = {
                    'id': chunk.id,
                    'story_id': chunk.story_id,
                    'chunk_text': chunk.chunk_text,
                    'chunk_context': chunk.chunk_context,
                    'chunk_order': chunk.chunk_order,
                    'chunk_type': chunk.chunk_type,
                    'overlap_start': chunk.overlap_start,
                    'overlap_end': chunk.overlap_end,
                    'chunk_length': chunk.chunk_length,
                    'chunk_word_count': chunk.chunk_word_count,
                    'semantic_keywords': chunk.semantic_keywords,
                    'content_embedding': chunk.content_embedding,
                    'search_embedding': chunk.search_embedding,
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_version': '2024-01',
                    'created_at': datetime.utcnow()
                }
                chunk_dicts.append(chunk_dict)
            
            # Save to database
            success = await self.db_manager.save_chunks_to_silver(chunk_dicts)
            
            if success:
                # Update story status to completed
                await self.db_manager.update_story_processing_status(
                    story_id, 
                    'completed',
                    {
                        'chunks_generated': len(story_chunks),
                        'quality_score': quality_score,
                        'processing_time': (datetime.utcnow() - datetime.fromisoformat(
                            story_data.get('processing_start_time', datetime.utcnow().isoformat())
                        )).total_seconds()
                    }
                )
                
                self.stats['processed'] += 1
                self.stats['total_chunks'] += len(story_chunks)
                print(f"✅ Successfully processed {len(story_chunks)} chunks")
                return True
            else:
                await self.db_manager.update_story_processing_status(story_id, 'failed_db_save')
                self.stats['failed'] += 1
                return False
                
        except Exception as e:
            error_msg = f"Error processing story {story_id}: {str(e)}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            self.stats['failed'] += 1
            
            await self.db_manager.update_story_processing_status(
                story_id, 
                'failed_error',
                {'error': str(e)}
            )
            return False
    
    async def process_batch(self, batch_size: int = 10) -> Dict:
        """Process multiple stories in batch"""
        self.stats['start_time'] = datetime.utcnow()
        
        try:
            # Get unprocessed stories
            stories = await self.db_manager.get_unprocessed_stories(batch_size)
            
            if not stories:
                print("📭 No stories to process")
                return self.stats
            
            print(f"📚 Processing batch of {len(stories)} stories...")
            
            # Process stories with controlled concurrency
            semaphore = asyncio.Semaphore(3)  # Limit concurrent processing
            
            async def process_with_semaphore(story):
                async with semaphore:
                    return await self.process_single_story(story)
            
            # Process all stories concurrently
            tasks = [process_with_semaphore(story) for story in stories]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            successes = sum(1 for r in results if r is True)
            failures = sum(1 for r in results if r is False or isinstance(r, Exception))
            
            print(f"📊 Batch complete: {successes} succeeded, {failures} failed")
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - self.stats['start_time']).total_seconds()
            self.stats['processing_time'] = processing_time
            self.stats['stories_per_minute'] = (successes / processing_time) * 60 if processing_time > 0 else 0
            
            return self.stats
            
        except Exception as e:
            print(f"❌ Batch processing error: {e}")
            self.stats['errors'].append(f"Batch error: {str(e)}")
            return self.stats
    
    async def run_continuous_processing(self, batch_size: int = 10, interval_seconds: int = 300):
        """Run continuous processing with specified intervals"""
        print(f"🔄 Starting continuous processing (batch_size={batch_size}, interval={interval_seconds}s)")
        
        try:
            while True:
                print(f"\n{'='*50}")
                print(f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - Starting new batch")
                
                # Process batch
                batch_stats = await self.process_batch(batch_size)
                
                # Print statistics
                await self.print_statistics()
                
                # Wait for next interval
                print(f"💤 Waiting {interval_seconds} seconds until next batch...")
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n🛑 Continuous processing stopped by user")
        except Exception as e:
            print(f"❌ Continuous processing error: {e}")
        finally:
            await self.cleanup()
    
    async def print_statistics(self):
        """Print current processing statistics"""
        # Get database stats
        db_stats = await self.db_manager.get_processing_stats()
        
        # Calculate embedding costs
        estimated_cost = self.embedding_generator.estimate_cost(
            self.stats['total_chunks'], 
            avg_tokens_per_chunk=100
        )
        
        print(f"""
📊 Processing Statistics:
   Stories Processed: {self.stats['processed']}
   Stories Failed: {self.stats['failed']}
   Total Chunks Generated: {self.stats['total_chunks']}
   Processing Rate: {self.stats.get('stories_per_minute', 0):.1f} stories/min
   
📈 Database Statistics:
   Total Stories: {db_stats.get('total_stories', 0)}
   Processed Stories: {db_stats.get('processed_stories', 0)}
   Pending Stories: {db_stats.get('pending_stories', 0)}
   Total Chunks: {db_stats.get('total_chunks', 0)}
   Avg Chunks/Story: {db_stats.get('avg_chunks_per_story', 0):.1f}
   
💰 Cost Estimation:
   Embedding Cost: ${estimated_cost:.4f}
   
❌ Recent Errors: {len(self.stats['errors'])}
""")
        
        # Show recent errors if any
        if self.stats['errors']:
            print("Recent Errors:")
            for error in self.stats['errors'][-3:]:  # Show last 3 errors
                print(f"   • {error}")
    
    async def cleanup(self):
        """Cleanup resources"""
        print("🧹 Cleaning up resources...")
        await self.db_manager.disconnect()
        print("✅ Cleanup completed")

# CLI interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Story Chunking Pipeline")
    parser.add_argument('--batch-size', type=int, default=10, help='Number of stories to process per batch')
    parser.add_argument('--continuous', action='store_true', help='Run continuous processing')
    parser.add_argument('--interval', type=int, default=300, help='Interval between batches in seconds')
    parser.add_argument('--stats-only', action='store_true', help='Show statistics only')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = ChunkingPipeline()
    
    try:
        await pipeline.initialize()
        
        if args.stats_only:
            # Just show statistics
            await pipeline.print_statistics()
        elif args.continuous:
            # Run continuous processing
            await pipeline.run_continuous_processing(args.batch_size, args.interval)
        else:
            # Run single batch
            stats = await pipeline.process_batch(args.batch_size)
            await pipeline.print_statistics()
            
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
    finally:
        await pipeline.cleanup()

if __name__ == "__main__":
    asyncio.run(main())