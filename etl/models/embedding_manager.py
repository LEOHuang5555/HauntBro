"""
Multi-Model Embedding Manager
Coordinates embedding generation with cost optimization for medallion architecture
"""

import asyncio
from openai import OpenAI
import numpy as np
from typing import List, Dict, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
import re

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.config.config import CONFIG

# Optional imports for alternative embedding models
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    success: bool
    content_embedding: Optional[List[float]]
    search_embedding: Optional[List[float]]
    model_used: str
    processing_time_ms: int
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class BatchEmbeddingResult:
    """Result of batch embedding generation"""
    success: bool
    embeddings: List[EmbeddingResult]
    total_processing_time_ms: int
    batch_size: int
    failed_count: int
    metadata: Optional[Dict] = None


class EmbeddingManager:
    """
    Multi-model embedding manager with cost optimization
    Supports OpenAI, Sentence Transformers, and custom models
    """
    
    def __init__(self):
        """Initialize embedding manager with multiple model options"""
        self.openai_config = CONFIG["openai"]
        self.embedding_config = CONFIG["embedding"]
        self.model_config = CONFIG["model"]
        
        # Model instances
        self.openai_client = None
        self.sentence_transformer = None
        self.chinese_transformer = None
        
        # Use model configurations from EmbeddingConfig to avoid conflicts
        self.model_configs = {
            'openai_small': self.embedding_config.openai_small,
            'openai_large': self.embedding_config.openai_large,
            'sentence_transformer_multilingual': self.embedding_config.sentence_transformer_multilingual,
            'sentence_transformer_english': self.embedding_config.sentence_transformer_english
        }
        
        # Performance tracking
        self.performance_stats = {
            'openai_avg_time': 0.0,
            'sentence_transformer_avg_time': 0.0,
            'total_requests': 0,
            'failed_requests': 0
        }
    
    async def initialize(self) -> bool:
        """Initialize embedding models"""
        try:
            # Initialize OpenAI
            if self.openai_config.api_key:
                self.openai_client = OpenAI(api_key=self.openai_config.api_key)
                print("✅ OpenAI embedding client initialized")
            else:
                print("⚠️  OpenAI API key not found - OpenAI embeddings unavailable")
                self.openai_client = None
            
            # Initialize Sentence Transformers
            if SENTENCE_TRANSFORMERS_AVAILABLE and TORCH_AVAILABLE:
                try:
                    print("Loading multilingual sentence transformer...")
                    self.sentence_transformer = SentenceTransformer(
                        self.embedding_config.sentence_transformer_multilingual['model']
                    )
                    
                    print("Loading English-optimized sentence transformer...")
                    self.chinese_transformer = SentenceTransformer(
                        self.embedding_config.sentence_transformer_english['model']
                    )
                    
                    print("✅ Sentence Transformer models loaded")
                    
                except Exception as e:
                    print(f"⚠️  Sentence Transformers initialization failed: {e}")
                    self.sentence_transformer = None
                    self.chinese_transformer = None
            else:
                print("⚠️  Sentence Transformers not available")
            
            return True
            
        except Exception as e:
            print(f"❌ Embedding manager initialization failed: {e}")
            return False
    
    async def _generate_openai_embedding(self, text: str, model_name: str = 'text-embedding-3-small') -> Tuple[List[float], int]:
        """Generate embedding using OpenAI API"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
            
        start_time = datetime.now()
        
        try:
            # Truncate text if too long (OpenAI has context limits)
            max_length = 8000  # Conservative limit
            if len(text) > max_length:
                text = text[:max_length]
            
            # Call OpenAI API
            response = await asyncio.to_thread(
                self.openai_client.embeddings.create,
                input=text,
                model=model_name
            )
            
            embedding = response.data[0].embedding

            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return embedding, processing_time_ms
            
        except Exception as e:
            print(f"❌ OpenAI embedding failed: {e}")
            raise e
    
    def _generate_sentence_transformer_embedding(self, text: str, language: str = 'multilingual') -> Tuple[List[float], int]:
        """Generate embedding using Sentence Transformers"""
        start_time = datetime.now()
        
        try:
            # Choose appropriate model based on language
            if language == 'zh' and self.chinese_transformer:
                model = self.chinese_transformer
            elif self.sentence_transformer:
                model = self.sentence_transformer
            else:
                raise RuntimeError("No Sentence Transformer model available")
            
            # Generate embedding
            embedding = model.encode(text, convert_to_tensor=False)
            
            # Convert to list if numpy array
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                        
            return embedding, processing_time_ms
            
        except Exception as e:
            print(f"❌ Sentence Transformer embedding failed: {e}")
            raise e
    
    async def generate_embeddings(
        self,
        text: str,
        search_text: List[str],
        language: str = "auto",
        strategy: str = "cost_optimized"
    ) -> EmbeddingResult:
        """
        Generate content and search embeddings with cost optimization
        
        Args:
            text: Text to embed
            language: Language hint ('zh', 'en', 'auto')
            strategy: Embedding strategy ('cost_optimized', 'quality_optimized', 'speed_optimized')
            
        Returns:
            EmbeddingResult with content and search embeddings
        """
        start_time = datetime.now()
        
        try:
            # Auto-detect language if not specified
            if language == "auto":
                chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
                total_chars = len(text.replace(' ', ''))
                language = 'zh' if (chinese_chars / max(total_chars, 1)) > 0.3 else 'en'
            
            # Combine text and context for content embedding
            content_text = text.strip()
            if not search_text:
                search_text = text  # Use main text for search embedding
            
            content_embedding = None
            search_embedding = None
            model_used = ""
            
            # Choose embedding strategy
            if strategy == "cost_optimized":
                # Use free models first, fallback to paid
                try:
                    content_embedding, time1 = await self._generate_openai_embedding(
                        content_text, 'text-embedding-3-small'
                    )
                    search_embedding, time2 = await self._generate_openai_embedding(
                        search_text, 'text-embedding-3-small'
                    )
                    model_used = "openai_small_speed"
                        
                except Exception as e:
                    # Fallback to sentence_transformer
                    print(f"⚠️  Cost-optimized embedding failed, trying sentence_transformer: {e}")
                    if SENTENCE_TRANSFORMERS_AVAILABLE and self.sentence_transformer:
                        content_embedding, content_time = self._generate_sentence_transformer_embedding(
                            content_text, language
                        )
                        search_embedding, search_time = self._generate_sentence_transformer_embedding(
                            search_text, language
                        )
                        model_used = "sentence_transformer_multilingual"
                    else:
                        raise RuntimeError("Sentence Transformers not available")
            
            elif strategy == "quality_optimized":
                # Use high-quality OpenAI model
                if self.openai_config.api_key:
                    content_embedding, time1 = await self._generate_openai_embedding(
                        content_text, 'text-embedding-3-large'
                    )
                    search_embedding, time2 = await self._generate_openai_embedding(
                        search_text, 'text-embedding-3-large'
                    )
                    model_used = "openai_large"
                else:
                    # Fallback to sentence transformers
                    content_embedding, content_time = self._generate_sentence_transformer_embedding(
                        content_text, language
                    )
                    search_embedding, search_time = self._generate_sentence_transformer_embedding(
                        search_text, language
                    )
                    model_used = "sentence_transformer_quality_fallback"
            
            elif strategy == "speed_optimized":
                # Use fastest available model
                if SENTENCE_TRANSFORMERS_AVAILABLE and self.sentence_transformer:
                    content_embedding, content_time = self._generate_sentence_transformer_embedding(
                        content_text, language
                    )
                    search_embedding, search_time = self._generate_sentence_transformer_embedding(
                        search_text, language
                    )
                    model_used = "sentence_transformer_speed"
                else:
                    # Use OpenAI small model for speed
                    content_embedding, time1 = await self._generate_openai_embedding(
                        content_text, 'text-embedding-3-small'
                    )
                    search_embedding, time2 = await self._generate_openai_embedding(
                        search_text, 'text-embedding-3-small'
                    )
                    model_used = "openai_small_speed"
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            
            result = EmbeddingResult(
                success=True,
                content_embedding=content_embedding,
                search_embedding=search_embedding,
                model_used=model_used,
                processing_time_ms=processing_time_ms,
                metadata={
                    'language_detected': language,
                    'strategy_used': strategy,
                    'content_text_length': len(content_text),
                    'embedding_dimensions': len(content_embedding) if content_embedding else 0
                }
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Embedding generation failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            return EmbeddingResult(
                success=False,
                content_embedding=None,
                search_embedding=None,
                model_used="failed",
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error_message=error_msg
            )
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        contexts: List[str] = None,
        language: str = "auto",
        strategy: str = "cost_optimized",
        batch_size: int = None
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts with optimized batching
        
        Args:
            texts: List of texts to embed
            contexts: Optional list of contexts (same length as texts)
            language: Language hint
            strategy: Embedding strategy
            batch_size: Custom batch size (uses model default if None)
            
        Returns:
            BatchEmbeddingResult with all embeddings
        """
        start_time = datetime.now()
        
        if not texts:
            return BatchEmbeddingResult(
                success=False,
                embeddings=[],
                total_processing_time_ms=0,
                batch_size=0,
                failed_count=0
            )
        
        # Prepare contexts
        if contexts is None:
            contexts = [""] * len(texts)
        elif len(contexts) != len(texts):
            contexts.extend([""] * (len(texts) - len(contexts)))
        
        # Determine optimal batch size
        if batch_size is None:
            if strategy == "cost_optimized" and SENTENCE_TRANSFORMERS_AVAILABLE:
                batch_size = self.embedding_config.batch_size_sentence_transformer
            else:
                batch_size = self.embedding_config.batch_size_openai
        
        embeddings = []
        failed_count = 0
        
        # Process in batches with controlled concurrency
        semaphore = asyncio.Semaphore(self.embedding_config.max_concurrent_requests)
        
        async def process_single_embedding(text, context):
            async with semaphore:
                return await self.generate_embeddings(text, context, language, strategy)
        
        # Process all texts
        tasks = [
            process_single_embedding(text, context)
            for text, context in zip(texts, contexts)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"❌ Batch item {i} failed with exception: {result}")
                failed_count += 1
                embeddings.append(EmbeddingResult(
                    success=False,
                    content_embedding=None,
                    search_embedding=None,
                    model_used="failed",
                    processing_time_ms=0,
                    error_message=str(result)
                ))
            else:
                embeddings.append(result)
                if not result.success:
                    failed_count += 1
        
        total_processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        batch_result = BatchEmbeddingResult(
            success=failed_count == 0,
            embeddings=embeddings,
            total_processing_time_ms=total_processing_time_ms,
            batch_size=len(texts),
            failed_count=failed_count,
            metadata={
                'strategy_used': strategy,
                'language': language,
                'avg_processing_time_per_item': total_processing_time_ms / len(texts) if texts else 0,
                'success_rate': (len(texts) - failed_count) / len(texts) if texts else 0
            }
        )
                
        return batch_result
    

# CLI interface for testing
async def main():
    """Test CLI for embedding manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Embedding Manager")
    parser.add_argument('--text', type=str, help='Text to embed')
    parser.add_argument('--file', type=str, help='File containing texts (one per line)')
    parser.add_argument('--strategy', choices=['cost_optimized', 'quality_optimized', 'speed_optimized'], 
                       default='cost_optimized', help='Embedding strategy')
    parser.add_argument('--language', choices=['zh', 'en', 'auto'], default='auto', help='Language hint')
    parser.add_argument('--stats', action='store_true', help='Show cost analysis')
    parser.add_argument('--capabilities', action='store_true', help='Show model capabilities')
    
    args = parser.parse_args()
    
    manager = EmbeddingManager()
    
    try:
        if not await manager.initialize():
            print("❌ Failed to initialize embedding manager")
            return
        
        texts = []
        if args.text:
            texts = [args.text]
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                texts = [line.strip() for line in f.readlines() if line.strip()]
        
        if texts:
            if len(texts) == 1:
                result = await manager.generate_embeddings(
                    texts[0], language=args.language, strategy=args.strategy
                )
                
                if result.success:
                    print(f"\n✅ Embedding successful:")
                    print(f"   Model used: {result.model_used}")
                    print(f"   Processing time: {result.processing_time_ms}ms")
                    print(f"   Content embedding dims: {len(result.content_embedding)}")
                    print(f"   Search embedding dims: {len(result.search_embedding)}")
                else:
                    print(f"❌ Embedding failed: {result.error_message}")
            else:
                batch_result = await manager.generate_batch_embeddings(
                    texts, language=args.language, strategy=args.strategy
                )
                
                print(f"\n📊 Batch Results:")
                print(f"   Total items: {batch_result.batch_size}")
                print(f"   Successful: {batch_result.batch_size - batch_result.failed_count}")
                print(f"   Failed: {batch_result.failed_count}")
                print(f"   Total time: {batch_result.total_processing_time_ms}ms")
    
        
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())