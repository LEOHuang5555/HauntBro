name: "Apache Airflow ETL Orchestration System - Ghost Story Search Engine"
description: |

## Goal
Implement a comprehensive Apache Airflow system that orchestrates all ETL processes for the ghost story search engine, managing medallion architecture workflows (Bronze → Silver → Gold), providing real-time monitoring, email notifications, and handling error recovery across PTT and Reddit data pipelines.

## Why
- **Business Value**: Automate the entire data pipeline from raw story scraping to searchable content, reducing manual intervention by 95%
- **Integration**: Creates a centralized orchestration layer that coordinates existing scrapers, processing, and analytics components
- **Problems Solved**: Eliminates manual pipeline management, provides proactive failure alerting, ensures data quality consistency, and optimizes resource costs through intelligent scheduling

## What
Build a production-ready Airflow system with:
- **3 Main DAGs**: PTT processing, Reddit processing, and cross-platform analytics
- **Custom Operators**: Wrapping existing scrapers and processing components
- **Email Notifications**: Gmail integration for failure/success alerts
- **SLA Monitoring**: Track pipeline performance with automated alerting
- **Error Handling**: Comprehensive retry mechanisms and dead letter queue management
- **Resource Optimization**: Cost-efficient scheduling and worker allocation

### Success Criteria
- [ ] Pipeline uptime >99.5% across all DAGs with minimal manual intervention
- [ ] SLA compliance >95% of pipelines complete within defined time windows
- [ ] Email delivery 100% notification delivery for critical events within 2 minutes
- [ ] Error recovery >90% of transient failures recover automatically
- [ ] Resource efficiency <$200/month in cloud compute costs with optimized scheduling
- [ ] Data quality >95% pass rate for all Great Expectations validation checks

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://airflow.apache.org/docs/apache-airflow/2.5.2/best-practices.html
  why: Airflow 2.5 best practices for DAG design, custom operators, and performance
  
- url: https://www.astronomer.io/docs/learn/error-notifications-in-airflow/
  why: Email notification setup and DAG-level callback patterns
  
- url: https://www.astronomer.io/docs/learn/airflow-great-expectations/
  why: Great Expectations integration with GreatExpectationsOperator
  
- url: https://vivasoftltd.com/great-expectations-with-airflow/
  why: Data quality integration patterns and checkpoint configuration
  
- url: https://medium.com/@prabakar193/medallion-architecture-a-step-by-step-guide-to-multi-hop-data-processing-563e26e8bf7a
  why: Medallion architecture orchestration with Airflow, Kafka integration patterns
  
- url: https://airflow.apache.org/docs/apache-airflow/stable/howto/custom-operator.html
  why: Official custom operator development guide for BaseOperator subclassing
  
- file: examples/etl/processing/pipeline.py
  why: Existing async processing patterns, error handling, and database integration
  
- file: examples/etl/processing/config.py
  why: Configuration patterns using dataclasses and environment variables
  
- file: examples/etl/web-scraper/scrapers/ptt_marvel_scraper.py
  why: PTT scraping implementation to wrap in custom operator
  
- file: examples/etl/web-scraper/scrapers/reddit_scraper.py
  why: Reddit API integration patterns and rate limiting
  
- file: examples/infrastructure/database/models.py
  why: Medallion architecture database schema (Bronze/Silver/Gold layers)
  
- file: examples/etl/processing/database.py
  why: Database connection pooling and async query patterns
  
- file: CLAUDE.md
  why: Development workflow requirements, Poetry usage, testing patterns, error handling standards
```

### Current Codebase Tree
```bash
examples/
├── etl/
│   ├── processing/
│   │   ├── chunking.py          # Story chunking logic
│   │   ├── config.py            # Configuration dataclasses
│   │   ├── database.py          # Async database operations
│   │   ├── embedding.py         # OpenAI embedding generation
│   │   ├── pipeline.py          # Main processing orchestrator
│   │   └── quality_score.py     # Content quality assessment
│   └── web-scraper/
│       └── scrapers/
│           ├── ptt_marvel_scraper.py    # PTT scraping implementation
│           └── reddit_scraper.py        # Reddit API client
├── infrastructure/
│   ├── airflow/
│   │   ├── config/              # Empty - needs setup
│   │   ├── dags/                # Empty - needs DAG implementations
│   │   └── operators/           # Empty - needs custom operators
│   └── database/
│       └── models.py            # Medallion architecture models
└── monitoring/
    └── alert/
        └── send_email.py        # Basic email sending utility
```

### Desired Codebase Tree with New Files
```bash
examples/infrastructure/airflow/
├── docker-compose.yml           # Airflow services with PostgreSQL, Redis
├── Dockerfile                   # Custom Airflow image with dependencies
├── airflow.cfg                  # Airflow configuration with email settings
├── requirements.txt             # Airflow providers and dependencies
├── config/
│   ├── __init__.py
│   ├── settings.py              # Airflow settings using existing config pattern
│   └── email_templates.py       # Jinja email templates
├── dags/
│   ├── __init__.py
│   ├── ptt_etl_dag.py          # PTT processing DAG (Daily, 4hr SLA)
│   ├── reddit_etl_dag.py       # Reddit processing DAG (6hr, 2hr SLA)
│   └── analytics_dag.py        # Cross-platform analytics (Daily, 1hr SLA)
├── operators/
│   ├── __init__.py
│   ├── base_operator.py        # Common operator functionality
│   ├── ptt_scraping_operator.py      # Wraps existing PTT scraper
│   ├── reddit_scraping_operator.py   # Wraps existing Reddit scraper
│   ├── embedding_operator.py         # Wraps existing embedding pipeline
│   └── data_quality_operator.py      # Great Expectations integration
├── plugins/
│   ├── __init__.py
│   └── email_callbacks.py      # Custom email notification callbacks
└── tests/
    ├── __init__.py
    ├── test_operators.py       # Unit tests for custom operators
    ├── test_dags.py           # DAG validation tests
    └── conftest.py            # Pytest configuration
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Airflow 2.5 requires specific setup
# - Custom operators must inherit from BaseOperator
# - Never perform expensive operations in __init__ method
# - Use Poetry for dependency management in Docker build
# - Email backend requires SMTP configuration in airflow.cfg

# CRITICAL: Poetry integration in Docker
# - Must activate Poetry shell for all operations: poetry shell
# - Use poetry add for new dependencies, not pip install
# - Docker build must use multi-stage with Poetry

# CRITICAL: Existing codebase integration
# - All scrapers use async/await patterns - must handle in operators
# - Database uses asyncpg connection pooling - maintain in operators  
# - Configuration uses dataclasses with environment variables
# - Error handling uses custom exceptions - preserve in operators

# CRITICAL: Great Expectations integration
# - Requires GreatExpectationsOperator from astronomer-providers
# - Checkpoints must be configured for each data validation
# - Data validation failures should trigger email alerts

# CRITICAL: Resource management
# - Use Airflow pools to limit concurrent operations
# - PTT scraping is rate-limited - max 1 request per second
# - Reddit API has strict rate limits - use existing backoff logic
# - Embedding generation is expensive - batch operations

# CRITICAL: Email configuration
# - Gmail requires app-specific passwords, not regular passwords
# - Email templates use Jinja2 - must escape variables properly
# - SLA notifications only work for scheduled DAGs, not manual triggers
```

## Implementation Blueprint

### Data Models and Structure
```python
# Reuse existing models from examples/infrastructure/database/models.py
# Bronze Layer: BronzeStory (raw scraped data)
# Silver Layer: SilverStory, SilverStoryChunks (processed data)  
# Gold Layer: GoldStoryPerformance, GoldUserAnalytics (business metrics)

# New configuration models following existing pattern
@dataclass
class AirflowConfig:
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_from: str = os.getenv("AIRFLOW_EMAIL_FROM", "")
    email_password: str = os.getenv("AIRFLOW_EMAIL_PASSWORD", "")
    
@dataclass  
class DAGConfig:
    ptt_schedule: str = "0 2 * * *"  # Daily at 2 AM UTC
    reddit_schedule: str = "0 */6 * * *"  # Every 6 hours
    analytics_schedule: str = "0 8 * * *"  # Daily at 8 AM UTC
    
    ptt_sla_hours: int = 4
    reddit_sla_hours: int = 2
    analytics_sla_hours: int = 1
```

### List of Tasks to Complete (In Order)

```yaml
Task 1: Infrastructure Setup
MODIFY examples/infrastructure/airflow/:
  - CREATE docker-compose.yml with Airflow 2.5+, PostgreSQL, Redis services
  - CREATE Dockerfile with Poetry integration following existing patterns
  - CREATE airflow.cfg with email SMTP configuration
  - CREATE requirements.txt with airflow providers

Task 2: Configuration Module  
CREATE examples/infrastructure/airflow/config/settings.py:
  - MIRROR pattern from: examples/etl/processing/config.py
  - ADD AirflowConfig, DAGConfig dataclasses with environment variables
  - PRESERVE existing configuration patterns from CLAUDE.md

Task 3: Base Operator Foundation
CREATE examples/infrastructure/airflow/operators/base_operator.py:
  - INHERIT from BaseOperator following Airflow best practices
  - ADD common error handling, logging, and database connection patterns
  - INTEGRATE existing async patterns from examples/etl/processing/

Task 4: PTT Scraping Operator
CREATE examples/infrastructure/airflow/operators/ptt_scraping_operator.py:
  - WRAP existing PTTMarvelScraper from examples/etl/web-scraper/scrapers/ptt_marvel_scraper.py
  - PRESERVE rate limiting and error handling logic
  - ADD Bronze layer data insertion using existing database models

Task 5: Reddit Scraping Operator  
CREATE examples/infrastructure/airflow/operators/reddit_scraping_operator.py:
  - WRAP existing Reddit scraper from examples/etl/web-scraper/scrapers/reddit_scraper.py
  - MAINTAIN existing PRAW integration and rate limiting
  - ADD Bronze layer data insertion with proper error handling

Task 6: Embedding Generation Operator
CREATE examples/infrastructure/airflow/operators/embedding_operator.py:
  - WRAP existing pipeline from examples/etl/processing/pipeline.py
  - MAINTAIN async processing patterns and OpenAI integration
  - ADD Silver layer chunk processing and Gold layer updates

Task 7: Data Quality Operator
CREATE examples/infrastructure/airflow/operators/data_quality_operator.py:
  - INTEGRATE Great Expectations using GreatExpectationsOperator patterns
  - ADD data validation for Bronze → Silver → Gold transformations
  - PRESERVE existing quality scoring from examples/etl/processing/quality_score.py

Task 8: Email Notification System
CREATE examples/infrastructure/airflow/plugins/email_callbacks.py:
  - ADD custom callback functions for DAG-level notifications
  - CREATE Jinja2 email templates for success/failure scenarios
  - INTEGRATE with existing email utility from examples/monitoring/alert/send_email.py

Task 9: PTT ETL DAG Implementation
CREATE examples/infrastructure/airflow/dags/ptt_etl_dag.py:
  - CREATE DAG with Bronze → Silver → Gold task dependencies
  - SET daily schedule (2 AM UTC) with 4-hour SLA
  - ADD task pool assignments and retry configurations
  - IMPLEMENT email callbacks for success/failure notifications

Task 10: Reddit ETL DAG Implementation  
CREATE examples/infrastructure/airflow/dags/reddit_etl_dag.py:
  - CREATE DAG with API polling → processing flow
  - SET 6-hour schedule with 2-hour SLA and Reddit rate limit compliance
  - ADD proper error handling for API failures and backoff logic
  - INTEGRATE with existing Reddit scraper configurations

Task 11: Cross-Platform Analytics DAG
CREATE examples/infrastructure/airflow/dags/analytics_dag.py:
  - CREATE DAG with external task sensors waiting for PTT and Reddit completion
  - ADD cross-platform analysis and business metrics calculation
  - SET daily schedule (8 AM UTC) with 1-hour SLA  
  - IMPLEMENT Gold layer analytics updates

Task 12: Resource Management Setup
MODIFY examples/infrastructure/airflow/config/settings.py:
  - ADD Airflow pool configurations for resource allocation
  - CREATE cost optimization scheduling logic
  - ADD worker resource calculation based on workload

Task 13: Comprehensive Testing
CREATE examples/infrastructure/airflow/tests/:
  - ADD unit tests for all custom operators using existing pytest patterns
  - CREATE DAG validation tests ensuring proper dependencies
  - ADD integration tests with database and email systems
  - FOLLOW existing testing workflow from CLAUDE.md
```

### Per Task Pseudocode

```python
# Task 3: Base Operator Foundation
class BaseGhostStoryOperator(BaseOperator):
    """Base operator with common functionality"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # PATTERN: Never do expensive operations in __init__
        self.config = CONFIG  # Use existing config pattern
    
    async def get_db_connection(self):
        # PATTERN: Reuse existing database connection from examples/etl/processing/database.py
        return await DatabaseManager().connect()
    
    def execute(self, context):
        # PATTERN: Wrap async execution for Airflow compatibility
        return asyncio.run(self.async_execute(context))
    
    async def async_execute(self, context):
        # CRITICAL: Override in subclasses
        raise NotImplementedError

# Task 4: PTT Scraping Operator  
class PTTScrapingOperator(BaseGhostStoryOperator):
    def __init__(self, board_name: str, date_range: dict, **kwargs):
        super().__init__(**kwargs)
        self.board_name = board_name
        self.date_range = date_range
    
    async def async_execute(self, context):
        # PATTERN: Reuse existing PTTMarvelScraper
        from examples.etl.web_scraper.scrapers.ptt_marvel_scraper import PTTMarvelScraper
        
        # GOTCHA: Rate limiting is built into existing scraper
        scraper = PTTMarvelScraper()
        
        # CRITICAL: Handle scraping errors with existing patterns
        try:
            stories = await scraper.scrape_board(self.board_name, self.date_range)
            
            # PATTERN: Use existing database models for Bronze layer
            db_manager = await self.get_db_connection()
            for story in stories:
                await db_manager.insert_bronze_story(story)
                
            return {"stories_scraped": len(stories)}
            
        except Exception as e:
            # PATTERN: Use existing error handling
            self.log.error(f"PTT scraping failed: {e}")
            raise

# Task 6: Embedding Generation Operator
class EmbeddingGenerationOperator(BaseGhostStoryOperator):
    def __init__(self, batch_size: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.batch_size = batch_size
    
    async def async_execute(self, context):
        # PATTERN: Reuse existing ChunkingPipeline from examples/etl/processing/pipeline.py
        from examples.etl.processing.pipeline import ChunkingPipeline
        
        # CRITICAL: Maintain existing async patterns and cost optimization
        pipeline = ChunkingPipeline()
        await pipeline.initialize()
        
        # GOTCHA: Embedding generation is expensive - use existing batching
        stats = await pipeline.process_batch(self.batch_size)
        
        # PATTERN: Return metrics for monitoring
        return {
            "stories_processed": stats["processed"],
            "chunks_generated": stats["total_chunks"],
            "cost_estimate": pipeline.embedding_generator.estimate_cost(
                stats["total_chunks"], avg_tokens_per_chunk=100
            )
        }
```

### Integration Points
```yaml
DATABASE:
  - connection: "Use existing asyncpg pool from examples/etl/processing/database.py"
  - models: "Leverage Bronze/Silver/Gold models from examples/infrastructure/database/models.py"
  - migrations: "No new tables needed - reuse existing medallion architecture"

EMAIL:
  - smtp: "Gmail integration with app-specific passwords in environment variables"
  - templates: "Jinja2 templates for failure/success/SLA notifications"
  - callbacks: "DAG-level and task-level callback functions"

MONITORING:
  - sla: "Task and DAG-level SLA monitoring with email alerts"
  - quality: "Great Expectations integration for data validation"
  - metrics: "Custom XCom variables for business metrics tracking"

RESOURCES:
  - pools: "ptt_processing_pool, reddit_api_pool, embedding_generation_pool, database_pool"
  - scheduling: "Off-peak scheduling for cost optimization"
  - scaling: "Dynamic resource allocation based on expected workload"
```

## Validation Loop

### Level 1: Syntax & Style  
```bash
# Run these FIRST - fix any errors before proceeding
poetry shell  # CRITICAL: Must activate Poetry environment
poetry add apache-airflow[postgres,celery,redis]==2.5.3
poetry add astronomer-providers[great-expectations]
poetry add great-expectations

# Code quality checks following CLAUDE.md requirements
poetry run black examples/infrastructure/airflow/ --check --diff
poetry run flake8 examples/infrastructure/airflow/ --max-line-length=88  
poetry run mypy examples/infrastructure/airflow/ --ignore-missing-imports

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# CREATE examples/infrastructure/airflow/tests/test_operators.py
import pytest
from unittest.mock import AsyncMock, patch
from examples.infrastructure.airflow.operators.ptt_scraping_operator import PTTScrapingOperator

@pytest.mark.asyncio
async def test_ptt_scraping_operator_success():
    """PTT scraping operator processes stories correctly"""
    operator = PTTScrapingOperator(
        task_id="test_ptt_scraping",
        board_name="marvel", 
        date_range={"start": "2024-01-01", "end": "2024-01-02"}
    )
    
    with patch('examples.etl.web_scraper.scrapers.ptt_marvel_scraper.PTTMarvelScraper') as mock_scraper:
        mock_scraper.return_value.scrape_board = AsyncMock(return_value=[
            {"title": "Test Story", "content": "Test content", "url": "test_url"}
        ])
        
        result = await operator.async_execute({})
        assert result["stories_scraped"] == 1

@pytest.mark.asyncio  
async def test_embedding_operator_batch_processing():
    """Embedding operator processes batches with cost tracking"""
    operator = EmbeddingGenerationOperator(task_id="test_embedding", batch_size=5)
    
    with patch('examples.etl.processing.pipeline.ChunkingPipeline') as mock_pipeline:
        mock_instance = mock_pipeline.return_value
        mock_instance.initialize = AsyncMock()
        mock_instance.process_batch = AsyncMock(return_value={
            "processed": 5, "total_chunks": 25, "failed": 0
        })
        mock_instance.embedding_generator.estimate_cost = lambda chunks, **kwargs: 0.05
        
        result = await operator.async_execute({})
        assert result["stories_processed"] == 5
        assert result["chunks_generated"] == 25
        assert result["cost_estimate"] == 0.05
```

```bash
# Run and iterate until passing:
poetry run pytest examples/infrastructure/airflow/tests/ -v --asyncio-mode=auto

# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: DAG Validation
```bash
# Start Airflow with Poetry
cd examples/infrastructure/airflow
poetry shell
poetry run airflow db init
poetry run airflow webserver --port 8080 &
poetry run airflow scheduler &

# Validate DAG imports without syntax errors
poetry run python -c "
import sys
sys.path.append('dags')
from ptt_etl_dag import dag as ptt_dag
from reddit_etl_dag import dag as reddit_dag  
from analytics_dag import dag as analytics_dag
print('✅ All DAGs imported successfully')
"

# Test DAG task dependencies
poetry run airflow dags test ptt_etl_dag 2024-01-01
poetry run airflow dags test reddit_etl_dag 2024-01-01

# Expected: DAGs execute without errors, email notifications sent
```

### Level 4: Integration Test
```bash
# Test email notification system
poetry run python -c "
from examples.infrastructure.airflow.plugins.email_callbacks import send_failure_email
from airflow.models import DagRun, TaskInstance
# Simulate failure notification
context = {'dag': type('obj', (object,), {'dag_id': 'test_dag'})}
send_failure_email(context)
print('✅ Email notification test passed')
"

# Test database integration  
poetry run python -c "
import asyncio
from examples.infrastructure.airflow.operators.ptt_scraping_operator import PTTScrapingOperator
operator = PTTScrapingOperator(task_id='test', board_name='marvel', date_range={})
# Test database connection
asyncio.run(operator.get_db_connection())
print('✅ Database integration test passed')
"
```

## Final Validation Checklist
- [ ] All tests pass: `poetry run pytest examples/infrastructure/airflow/tests/ -v`
- [ ] No linting errors: `poetry run flake8 examples/infrastructure/airflow/`
- [ ] No type errors: `poetry run mypy examples/infrastructure/airflow/`
- [ ] DAGs import successfully: `poetry run airflow dags list | grep -E "(ptt_etl|reddit_etl|analytics)"`
- [ ] Email notifications work: Manual test with failure callback
- [ ] Database integration works: Connection and query tests pass
- [ ] Resource pools configured: `poetry run airflow pools list`
- [ ] SLA monitoring active: Check Airflow UI for SLA configuration
- [ ] Docker setup works: `docker-compose up -d` starts all services
- [ ] Error cases handled gracefully: Test with invalid inputs
- [ ] Great Expectations integration: Data quality checks execute
- [ ] Cost optimization active: Off-peak scheduling configured

---

## Anti-Patterns to Avoid
- ❌ Don't create new scrapers - wrap existing ones in operators
- ❌ Don't ignore existing async patterns - maintain throughout Airflow integration  
- ❌ Don't skip Poetry activation - all commands must use `poetry run` or `poetry shell`
- ❌ Don't hardcode configuration - use existing environment variable patterns
- ❌ Don't create synchronous database operations - maintain async patterns
- ❌ Don't ignore existing error handling - preserve custom exception patterns
- ❌ Don't skip resource pools - use them to prevent resource contention
- ❌ Don't ignore rate limits - respect existing scraper rate limiting
- ❌ Don't skip email testing - verify SMTP configuration before deployment
- ❌ Don't ignore SLA configuration - set appropriate timeouts for each DAG

**PRP Confidence Score: 9/10**

This PRP provides comprehensive context from existing codebase patterns, external documentation, and detailed implementation steps. The high score reflects the thorough research, existing code reuse strategy, and detailed validation gates that should enable successful one-pass implementation. The only risk factor is the complexity of integrating multiple systems (Airflow + existing async code + email + monitoring), but the detailed pseudocode and existing pattern references mitigate this significantly.