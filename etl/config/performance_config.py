"""
Performance-Optimized Configuration for High-Speed ETL
Target: 100+ stories/minute processing
"""
import os
from dataclasses import dataclass, replace
from typing import Dict, Any
from .config import CONFIG

@dataclass
class PerformanceOptimizations:
    """Performance optimization settings"""
    # Concurrency settings
    max_concurrent_stories: int = 25  # Increased from 3
    max_concurrent_embeddings: int = 15  # Increased from 3
    batch_size: int = 50  # Larger batches
    
    # Processing speed optimizations
    min_quality_score: float = 0.3  # Lower threshold for speed
    target_chunk_size: int = 400  # Smaller chunks = faster processing
    max_chunks_per_story: int = 30  # Limit complexity
    
    # API optimization
    openai_timeout: int = 20  # Reduced timeout
    openai_max_retries: int = 2  # Fewer retries
    api_rate_limit_delay: float = 0.5  # Minimal delay
    
    # Embedding optimizations
    embedding_batch_size: int = 20  # Larger embedding batches
    skip_search_embeddings: bool = False  # Keep search embeddings for now
    
    # Model optimizations
    chinese_processor_timeout: int = 15  # Faster processing
    english_processor_timeout: int = 15  # Faster processing
    
    # Database optimizations
    db_connection_pool_size: int = 30  # More connections
    db_max_overflow: int = 20  # Higher overflow


def apply_performance_optimizations():
    """Apply performance optimizations to global CONFIG"""
    perf = PerformanceOptimizations()
    
    # Update chunking config for speed
    CONFIG["chunking"] = replace(CONFIG["chunking"],
        target_chunk_size=perf.target_chunk_size,
        min_quality_score=perf.min_quality_score,
        max_chunks_per_story=perf.max_chunks_per_story
    )
    
    # Update OpenAI config for speed
    CONFIG["openai"] = replace(CONFIG["openai"],
        timeout=perf.openai_timeout,
        max_retries=perf.openai_max_retries,
        embedding_batch_size=perf.embedding_batch_size
    )
    
    # Update embedding config for speed
    CONFIG["embedding"] = replace(CONFIG["embedding"],
        max_concurrent_requests=perf.max_concurrent_embeddings,
        batch_size_openai=perf.embedding_batch_size,
        batch_size_sentence_transformer=perf.embedding_batch_size
    )
    
    # Update database config for higher throughput
    CONFIG["database"] = replace(CONFIG["database"],
        max_connections=perf.db_connection_pool_size
    )
    
    print("⚡ Performance optimizations applied:")
    print(f"   Max Concurrent Stories: {perf.max_concurrent_stories}")
    print(f"   Chunk Size: {perf.target_chunk_size}")
    print(f"   Quality Threshold: {perf.min_quality_score}")
    print(f"   Embedding Batch Size: {perf.embedding_batch_size}")
    print(f"   DB Connections: {perf.db_connection_pool_size}")
    
    return perf


def get_speed_optimized_processor_config():
    """Get processor configuration optimized for speed"""
    return {
        'batch_processing': {
            'max_concurrent_stories': 25,
            'batch_size': 50,
            'inter_batch_delay': 0.1  # Minimal delay between batches
        },
        'quality_settings': {
            'min_quality_score': 0.3,
            'skip_quality_enhancement': True,  # Skip heavy quality improvements
            'fast_language_detection': True
        },
        'embedding_settings': {
            'strategy': 'speed_optimized',
            'batch_size': 20,
            'max_concurrent': 15,
            'skip_search_embeddings': False
        },
        'chunking_settings': {
            'target_size': 400,
            'max_chunks': 30,
            'overlap_reduction': True  # Reduce overlap for speed
        },
        'model_settings': {
            'temperature': 0.1,  # Lower temperature for faster generation
            'max_tokens_reduction': True,  # Use minimal token counts
            'timeout_aggressive': True
        }
    }


def benchmark_configuration():
    """Configuration specifically for benchmarking performance"""
    return {
        'test_mode': True,
        'target_stories': 100,  # Process 100 stories for benchmark
        'target_time_seconds': 60,  # Complete in 60 seconds
        'metrics_collection': {
            'detailed_timing': True,
            'bottleneck_detection': True,
            'resource_monitoring': True
        },
        'optimizations': {
            'aggressive_concurrency': True,
            'minimal_logging': True,
            'skip_non_essential': True
        }
    }


def production_speed_config():
    """Production-ready speed configuration"""
    return {
        'reliability': {
            'max_retries': 2,
            'timeout_seconds': 20,
            'error_threshold': 0.05  # 5% error rate tolerance
        },
        'throughput': {
            'target_stories_per_minute': 100,
            'max_concurrent_stories': 20,
            'batch_processing': True
        },
        'quality': {
            'min_acceptable_quality': 0.3,
            'quality_vs_speed_tradeoff': 'speed',  # Prioritize speed over quality
            'skip_complex_processing': True
        },
        'monitoring': {
            'real_time_metrics': True,
            'performance_alerts': True,
            'bottleneck_detection': True
        }
    }


# Global performance configuration
PERFORMANCE_CONFIG = get_speed_optimized_processor_config()
BENCHMARK_CONFIG = benchmark_configuration()
PRODUCTION_SPEED_CONFIG = production_speed_config()