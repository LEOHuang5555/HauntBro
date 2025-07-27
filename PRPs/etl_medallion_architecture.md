name: "ETL Medallion Architecture - Context-Rich Implementation PRP"
description: |

## Goal
Implement a comprehensive ETL system following the medallion model (Bronze → Silver → Gold) that transforms raw ghost story data from PTT (Traditional Chinese) and Reddit (English) through three distinct layers with quality assurance, monitoring, and business intelligence capabilities. The system must support both batch and real-time processing with multi-language text processing using DeepSeek (Chinese) and LLaMA (English), while maintaining <2 hours processing latency and >95% data quality scores.

## Why
- **Business Value**: Enables advanced search and analytics capabilities for the ghost story platform by providing clean, searchable, and analyzable data
- **User Impact**: Improves search relevance and recommendation quality through processed embeddings and semantic understanding
- **Integration**: Builds upon existing scraping infrastructure and database models to create a complete data pipeline
- **Problems Solved**: 
  - Raw scraped data is unstructured and difficult to search semantically
  - No unified processing pipeline for multi-language content (Chinese/English)
  - Lack of business intelligence and user behavior analytics
  - No data quality monitoring or lineage tracking

## What
A complete medallion architecture ETL pipeline with:
- **Bronze Layer**: Immutable raw data preservation with audit trails
- **Silver Layer**: Language-specific cleaning, chunking, and embedding generation
- **Gold Layer**: Business intelligence aggregations and user analytics
- **Airflow Orchestration**: Three coordinated DAGs (PTT_ETL, Reddit_ETL, Cross_Platform_Analytics)
- **Quality Framework**: Great Expectations for data validation and monitoring
- **Multi-language Processing**: DeepSeek for Chinese content, LLaMA for English content
- **Real-time Capabilities**: Kafka integration for streaming data processing

### Success Criteria
- [ ] ETL processing latency < 2 hours for daily batch processing, < 15 minutes for real-time updates
- [ ] Data quality score > 95% across all medallion layers with automated quality assurance
- [ ] Pipeline uptime > 99.5% with automated recovery and minimal manual intervention
- [ ] Cost optimization < $200/month for embedding generation and cloud infrastructure
- [ ] Processing throughput 10K+ stories per hour during peak processing periods
- [ ] Storage efficiency < 50% storage growth through deduplication and compression
- [ ] All validation gates pass without manual intervention

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://www.databricks.com/glossary/medallion-architecture
  why: Core medallion architecture patterns and layer definitions
  
- url: https://www.getdbt.com/blog/building-a-robust-data-pipeline-with-dbt-airflow-and-great-expectations
  why: Modern dAG stack (dbt, Airflow, Great Expectations) implementation patterns
  
- url: https://medium.com/@akriti.upadhyay/steps-to-build-chinese-language-ai-using-deepseek-and-qdrant-74e5cda604c0
  why: DeepSeek Chinese text processing and embedding pipeline patterns

- url: https://airflowsummit.org/sessions/2021/building-a-robust-data-pipeline-with-the-dag-stack/
  why: Airflow DAG orchestration patterns for ETL pipelines

- file: examples/etl/processing/pipeline.py
  why: Existing chunking pipeline pattern with async processing and database integration
  
- file: examples/etl/processing/database.py
  why: Database manager pattern for medallion layer operations
  
- file: examples/etl/web-scraper/etl/silver_derivation.md
  why: Silver layer transformation specifications and Python implementations
  
- file: examples/infrastructure/database/models.py
  why: Existing medallion architecture SQLAlchemy models (Bronze/Silver/Gold layers)
  
- file: examples/etl/processing/config.py
  why: Configuration patterns for multi-model and database connections

- docfile: PRPs/INITIAL_etl_medallion.md
  why: Complete feature specification with technical requirements and success criteria
```

### Current Codebase tree
```bash
examples/
├── etl/
│   ├── processing/
│   │   ├── chunking.py           # Story chunking with language detection
│   │   ├── config.py             # Multi-model and database configuration
│   │   ├── database.py           # DatabaseManager for medallion operations
│   │   ├── embedding.py          # Embedding generation with cost optimization
│   │   ├── model_setup.py        # DeepSeek/LLaMA model initialization
│   │   ├── pipeline.py           # ChunkingPipeline orchestrator
│   │   └── quality_score.py      # Content quality assessment
│   └── web-scraper/
│       ├── etl/
│       │   ├── gold_derivation.md    # Gold layer specifications
│       │   ├── ptt_etl_pure.py       # PTT processing patterns
│       │   ├── reddit_etl_pure.py    # Reddit processing patterns
│       │   └── silver_derivation.md  # Silver layer transformation specs
│       └── scrapers/
│           ├── ptt_marvel_scraper.py
│           └── reddit_scraper.py
├── infrastructure/
│   ├── airflow/
│   │   └── dags/
│   │       └── scraper.py        # Basic DAG pattern
│   ├── database/
│   │   ├── models.py             # Complete medallion SQLAlchemy models
│   │   └── schema.sql
│   └── kafka/
│       ├── consumers.py          # Kafka consumer patterns
│       └── producers.py          # Kafka producer patterns
└── monitoring/
    ├── alter/
    │   └── send_email.py         # Alert notification patterns
    └── dashboard/
        └── story_search_ranking.py
```

### Desired Codebase tree with files to be added
```bash
examples/
├── etl/
│   ├── medallion/
│   │   ├── __init__.py
│   │   ├── bronze_processor.py       # Bronze layer ingestion with immutable storage
│   │   ├── silver_processor.py       # Language-specific cleaning and chunking
│   │   ├── gold_processor.py         # Business intelligence aggregations
│   │   ├── quality_manager.py        # Great Expectations integration
│   │   └── lineage_tracker.py        # Data lineage and audit trails
│   ├── models/
│   │   ├── __init__.py
│   │   ├── chinese_processor.py      # DeepSeek integration for Chinese content
│   │   ├── english_processor.py      # LLaMA integration for English content
│   │   └── embedding_manager.py      # Multi-model embedding generation
│   └── orchestration/
│       ├── __init__.py
│       ├── ptt_etl_dag.py           # PTT processing DAG
│       ├── reddit_etl_dag.py        # Reddit processing DAG
│       ├── cross_platform_dag.py    # Combined analytics DAG
│       └── dag_factory.py           # DAG configuration factory
├── infrastructure/
│   ├── airflow/
│   │   ├── operators/
│   │   │   ├── medallion_operators.py # Custom operators for medallion processing
│   │   │   └── quality_operators.py   # Great Expectations operators
│   │   └── hooks/
│   │       └── medallion_hooks.py     # Database hooks for medallion layers
│   ├── monitoring/
│   │   ├── data_quality/
│   │   │   ├── expectations/          # Great Expectations suites
│   │   │   └── checkpoints/           # Quality checkpoints
│   │   └── dashboards/
│   │       └── medallion_metrics.py   # Pipeline monitoring dashboards
└── tests/
    ├── test_medallion/
    │   ├── test_bronze_processor.py
    │   ├── test_silver_processor.py
    │   └── test_gold_processor.py
    └── test_quality/
        └── test_data_expectations.py
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Poetry virtual environment must be activated
# poetry run python  # Required for all python script execution


# CRITICAL: PostgreSQL vector extension (pgvector) required for embeddings
# CREATE EXTENSION IF NOT EXISTS vector;
# Embeddings stored as VECTOR(1536) type
# Configuration is placed at `.env`

# CRITICAL: Airflow requires proper timezone handling
# from airflow.utils.dates import days_ago
# All datetime objects must be timezone-aware

# CRITICAL: Great Expectations context configuration required
# Must initialize DataContext with proper expectations store

# CRITICAL: Kafka exactly-once semantics requires idempotent producers
# producer_config = {'enable.idempotence': True, 'acks': 'all'}

# CRITICAL: LLaMA requires specific memory management for large texts
# Implement chunking before passing to model to avoid OOM errors

# CRITICAL: Database connection pooling essential for concurrent processing
# Use asyncpg.create_pool with min_size=5, max_size=20

# GOTCHA: Chinese text tokenization differs from English
# Use jieba for Chinese word segmentation, not standard split()
# Character-based counting for Chinese (1.5 chars per token avg)

# GOTCHA: Airflow DAG imports must be at module level
# Cannot use dynamic imports within DAG definitions
```

## Implementation Blueprint

### Data models and structure

Extend existing medallion models with ETL-specific metadata and processing status tracking:

```python
# Extend existing models in examples/infrastructure/database/models.py
class BronzeStoryProcessing(Base):
    """Processing metadata for bronze stories"""
    __tablename__ = 'bronze_story_processing'
    
    story_id = Column(PostgresUUID, ForeignKey('bronze_stories.id'), primary_key=True)
    processing_status = Column(String(20), default='pending')  # pending, processing, completed, failed
    etl_run_id = Column(String(100))  # Airflow run ID for lineage
    quality_checks = Column(JSONB)  # Great Expectations results
    processing_metadata = Column(JSONB)  # ETL metrics and timings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SilverStoryChunks(Base):
    """Enhanced chunk model with embedding metadata"""
    __tablename__ = 'silver_story_chunks'
    
    # Extend existing chunk fields

    processing_language = Column(String(10))  # 'zh', 'en', 'mixed'
    chunk_quality_score = Column(Float)  # Quality assessment per chunk
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Foundation - Database Schema Extensions
MODIFY examples/infrastructure/database/models.py:
  - ADD BronzeStoryProcessing model for ETL metadata tracking
  - ADD enhanced fields to existing SilverStoryChunks model
  - ADD GoldLayerMetrics model for business intelligence aggregations
  - PRESERVE existing relationships and constraints

CREATE examples/infrastructure/database/migrations/:
  - CREATE alembic migration for new tables and fields
  - INCLUDE proper indexes for performance optimization

Task 2: Bronze Layer - Immutable Data Ingestion
CREATE examples/etl/medallion/bronze_processor.py:
  - MIRROR pattern from: examples/etl/processing/database.py
  - IMPLEMENT immutable storage with audit trails
  - ADD Kafka integration for real-time ingestion
  - INCLUDE duplicate detection and deduplication logic

Task 3: Multi-Language Model Integration
CREATE examples/etl/models/chinese_processor.py:
  - MIRROR pattern from: examples/etl/processing/model_setup.py
  - IMPLEMENT DeepSeek integration for Traditional Chinese
  - ADD proper character encoding and normalization
  - INCLUDE error handling for model API failures

CREATE examples/etl/models/english_processor.py:
  - MIRROR pattern from: examples/etl/models/chinese_processor.py
  - IMPLEMENT LLaMA integration for English content
  - MODIFY for English-specific processing requirements
  - KEEP error handling pattern identical

Task 4: Silver Layer - Language-Specific Processing
CREATE examples/etl/medallion/silver_processor.py:
  - MIRROR pattern from: examples/etl/processing/pipeline.py
  - IMPLEMENT language detection and routing
  - ADD content cleaning and standardization
  - INCLUDE embedding generation with cost optimization
  - ADD semantic chunking with overlap management

Task 5: Gold Layer - Business Intelligence
CREATE examples/etl/medallion/gold_processor.py:
  - IMPLEMENT business metrics aggregations
  - ADD user behavior analytics calculations
  - INCLUDE cross-platform insights generation
  - ADD predictive analytics for recommendations

Task 6: Data Quality Framework
CREATE examples/etl/medallion/quality_manager.py:
  - IMPLEMENT Great Expectations integration
  - ADD data validation suites for each layer
  - INCLUDE anomaly detection and alerting
  - ADD data lineage tracking

CREATE examples/infrastructure/monitoring/data_quality/expectations/:
  - CREATE bronze_layer_expectations.json
  - CREATE silver_layer_expectations.json  
  - CREATE gold_layer_expectations.json

Task 7: Airflow DAG Orchestration
CREATE examples/etl/orchestration/ptt_etl_dag.py:
  - MIRROR pattern from: examples/infrastructure/airflow/dags/scraper.py
  - IMPLEMENT bronze → silver → gold processing flow
  - ADD Chinese-specific processing steps
  - INCLUDE error handling and retry logic

CREATE examples/etl/orchestration/reddit_etl_dag.py:
  - MIRROR pattern from: examples/etl/orchestration/ptt_etl_dag.py
  - MODIFY for English content processing
  - ADD Reddit-specific transformations
  - KEEP DAG structure identical for consistency

CREATE examples/etl/orchestration/cross_platform_dag.py:
  - IMPLEMENT combined analytics across platforms
  - ADD cross-language similarity analysis
  - INCLUDE business metrics aggregation
  - ADD dependency management with other DAGs

Task 8: Custom Airflow Operators
CREATE examples/infrastructure/airflow/operators/medallion_operators.py:
  - CREATE BronzeIngestionOperator
  - CREATE SilverProcessingOperator
  - CREATE GoldAggregationOperator
  - CREATE QualityCheckOperator (Great Expectations integration)

Task 9: Monitoring and Alerting
CREATE examples/infrastructure/monitoring/dashboards/medallion_metrics.py:
  - MIRROR pattern from: examples/monitoring/dashboard/story_search_ranking.py
  - IMPLEMENT real-time pipeline monitoring
  - ADD cost tracking and optimization alerts
  - INCLUDE data quality score dashboards

CREATE examples/infrastructure/monitoring/alerts/:
  - CREATE pipeline_failure_alerts.py
  - CREATE data_quality_alerts.py
  - CREATE cost_optimization_alerts.py

Task 10: Integration Testing and Validation
CREATE tests/test_medallion/:
  - CREATE comprehensive test suite for each processor
  - ADD integration tests for DAG execution
  - INCLUDE performance and load testing
  - ADD data quality validation tests
```

### Per task pseudocode as needed added to each task

```python
# Task 4: Silver Layer Processing
class SilverProcessor:
    def __init__(self):
        self.chinese_processor = ChineseProcessor()  # DeepSeek integration
        self.english_processor = EnglishProcessor()  # LLaMA integration
        self.embedding_manager = EmbeddingManager()
        self.quality_manager = QualityManager()
    
    async def process_story(self, bronze_story: BronzeStory) -> List[SilverChunk]:
        # PATTERN: Language detection first (see examples/etl/processing/pipeline.py)
        language = detect_language(bronze_story.content)
        
        # GOTCHA: Must normalize Chinese text before processing
        if language == 'zh':
            content = unicodedata.normalize('NFKC', bronze_story.content)
            chunks = await self.chinese_processor.chunk_story(content)
        else:
            chunks = await self.english_processor.chunk_story(bronze_story.content)
        
        # PATTERN: Generate embeddings in batches for cost optimization
        for batch in batch_chunks(chunks, size=100):  # OpenAI rate limit
            embeddings = await self.embedding_manager.generate_batch(batch)
            # CRITICAL: Track costs for optimization
            cost = calculate_embedding_cost(batch, model='text-embedding-3-small')
            
        # PATTERN: Quality validation before storage
        quality_score = await self.quality_manager.assess_chunks(chunks)
        if quality_score < 0.95:  # Configurable threshold
            raise QualityValidationError(f"Quality score {quality_score} below threshold")
        
        return chunks

# Task 7: Airflow DAG Structure
from airflow import DAG
from airflow.utils.dates import days_ago
from examples.infrastructure.airflow.operators.medallion_operators import (
    BronzeIngestionOperator, SilverProcessingOperator, GoldAggregationOperator
)

def create_ptt_etl_dag():
    dag = DAG(
        'ptt_etl_medallion',
        default_args={
            'depends_on_past': False,
            'start_date': days_ago(1),
            'email_on_failure': True,
            'email_on_retry': False,
            'retries': 2,
            'retry_delay': timedelta(minutes=5)
        },
        description='PTT Ghost Stories ETL - Medallion Architecture',
        schedule_interval='@hourly',  # Real-time processing requirement
        catchup=False,
        tags=['etl', 'medallion', 'ptt', 'chinese']
    )
    
    # PATTERN: Sequential layer processing with quality gates
    bronze_task = BronzeIngestionOperator(
        task_id='bronze_ingestion',
        source='ptt_marvel',
        dag=dag
    )
    
    silver_task = SilverProcessingOperator(
        task_id='silver_processing', 
        language='zh',
        model='deepseek',
        dag=dag
    )
    
    gold_task = GoldAggregationOperator(
        task_id='gold_aggregation',
        metrics=['story_performance', 'user_behavior'],
        dag=dag
    )
    
    # CRITICAL: Dependencies ensure data quality
    bronze_task >> silver_task >> gold_task
    
    return dag
```

### Integration Points
```yaml
DATABASE:
  - migration: "Add medallion processing metadata tables"
  - indexes: "CREATE INDEX idx_processing_status ON bronze_story_processing(processing_status)"
  - indexes: "CREATE INDEX idx_embedding_model ON silver_story_chunks(embedding_model_version)"
  
CONFIG:
  - add to: examples/etl/processing/config.py
  - pattern: "DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')"
  - pattern: "LLAMA_MODEL_PATH = os.getenv('LLAMA_MODEL_PATH', 'models/llama')"
  - pattern: "QUALITY_THRESHOLD = float(os.getenv('QUALITY_THRESHOLD', '0.95'))"
  
AIRFLOW:
  - add to: examples/infrastructure/airflow/dags/
  - pattern: "from examples.etl.orchestration import ptt_etl_dag, reddit_etl_dag"
  
KAFKA:
  - topics: "bronze_stories, silver_chunks, gold_metrics"
  - pattern: "exactly_once_semantics with idempotent producers"

MONITORING:
  - add to: examples/infrastructure/monitoring/
  - pattern: "Great Expectations DataContext with PostgreSQL metadata store"
  - alerts: "Email notifications for quality failures and pipeline errors"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
poetry shell  # CRITICAL: Virtual environment activation required

# Code quality checks
poetry run ruff check examples/etl/medallion/ --fix
poetry run mypy examples/etl/medallion/ --ignore-missing-imports
poetry run black examples/etl/medallion/ --check

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE tests/test_medallion/test_silver_processor.py
import pytest
from examples.etl.medallion.silver_processor import SilverProcessor
from examples.infrastructure.database.models import BronzeStory

@pytest.mark.asyncio
async def test_chinese_story_processing():
    """Chinese story processing with DeepSeek integration"""
    processor = SilverProcessor()
    
    # Test with Traditional Chinese content
    bronze_story = BronzeStory(
        content="這是一個恐怖的故事，發生在深夜的學校...",
        source="ptt_marvel",
        language="zh"
    )
    
    chunks = await processor.process_story(bronze_story)
    
    assert len(chunks) > 0
    assert all(chunk.processing_language == 'zh' for chunk in chunks)
    assert all(chunk.content_embedding is not None for chunk in chunks)
    assert all(chunk.chunk_quality_score >= 0.5 for chunk in chunks)

@pytest.mark.asyncio  
async def test_quality_validation_failure():
    """Quality validation prevents low-quality content"""
    processor = SilverProcessor()
    
    # Test with very short, low-quality content
    bronze_story = BronzeStory(content="test", source="test")
    
    with pytest.raises(QualityValidationError):
        await processor.process_story(bronze_story)

@pytest.mark.asyncio
async def test_embedding_cost_tracking():
    """Embedding costs are tracked for optimization"""
    processor = SilverProcessor()
    bronze_story = BronzeStory(
        content="A long English ghost story for testing...",
        source="reddit_ghoststories"
    )
    
    chunks = await processor.process_story(bronze_story)
    
    total_cost = sum(chunk.embedding_cost for chunk in chunks)
    assert total_cost > 0
    assert total_cost < 0.01  # Cost optimization requirement
```

```bash
# Run and iterate until passing:
poetry run pytest tests/test_medallion/ -v --asyncio-mode=auto

# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test - Airflow DAG Execution
```bash
# Start required services
docker-compose up -d postgres redis

# Initialize Airflow database
poetry run airflow db init

# Start Airflow scheduler and webserver
poetry run airflow scheduler &
poetry run airflow webserver &

# Test DAG parsing and execution
poetry run airflow dags test ptt_etl_medallion 2025-01-01

# Expected: DAG executes successfully through all tasks
# Check logs: tail -f logs/scheduler/latest/*.log
```

### Level 4: End-to-End Pipeline Test
```bash
# Start full system
docker-compose up -d  # PostgreSQL, Redis, Kafka

# Produce test data to Kafka
poetry run python -c "
from examples.infrastructure.kafka.producers import produce_test_story
produce_test_story('ptt_marvel', '測試故事內容...')
"

# Trigger DAG execution
poetry run airflow dags trigger ptt_etl_medallion

# Verify data flow through medallion layers
poetry run python -c "
from examples.etl.medallion.quality_manager import verify_pipeline
result = verify_pipeline('ptt_etl_medallion')
assert result.quality_score > 0.95
assert result.processing_time < 7200  # 2 hours max
print(f'Pipeline validation: {result}')
"

# Expected: Data flows Bronze → Silver → Gold with quality scores > 95%
```

## Final validation Checklist
- [ ] All tests pass: `poetry run pytest tests/ -v --asyncio-mode=auto`
- [ ] No linting errors: `poetry run ruff check examples/etl/`
- [ ] No type errors: `poetry run mypy examples/etl/ --ignore-missing-imports`
- [ ] Airflow DAGs parse successfully: `poetry run airflow dags list | grep etl`
- [ ] Great Expectations suites validate: `poetry run great_expectations checkpoint run bronze_checkpoint`
- [ ] Pipeline processes test data end-to-end within SLA (< 2 hours)
- [ ] Quality scores exceed 95% threshold across all layers
- [ ] Embedding costs remain under $200/month projected rate
- [ ] Multi-language processing works for both Chinese and English content
- [ ] Real-time processing latency < 15 minutes for streaming data
- [ ] Error handling gracefully manages API failures and retries

---

## Anti-Patterns to Avoid
- ❌ Don't bypass quality validation to "speed up" processing
- ❌ Don't process Chinese text without proper encoding normalization  
- ❌ Don't ignore embedding costs - implement batch processing and monitoring
- ❌ Don't create separate patterns for Chinese/English - use polymorphic design
- ❌ Don't skip data lineage tracking - essential for debugging and compliance
- ❌ Don't hardcode language detection - make it configurable and testable
- ❌ Don't use synchronous operations in Airflow tasks - all operations must be async-compatible
- ❌ Don't skip Great Expectations integration - data quality is non-negotiable
- ❌ Don't ignore Kafka exactly-once semantics - duplicate processing violates immutability
- ❌ Don't deploy without comprehensive monitoring - pipeline failures must be immediately detectable

---

## Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation including:
✅ Complete existing codebase analysis and patterns to follow
✅ External research on medallion architecture best practices  
✅ Specific DeepSeek and multi-language processing requirements
✅ Executable validation gates with proper async testing
✅ Integration with existing database models and infrastructure
✅ Comprehensive error handling and monitoring requirements
✅ Detailed implementation blueprint with task dependencies
✅ Performance and cost optimization requirements with measurable criteria

The implementation should succeed in one pass given the detailed context, existing patterns, and comprehensive validation framework provided.