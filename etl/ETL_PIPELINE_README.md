# HauntBro ETL Pipeline Execution Scripts

This documentation provides a comprehensive guide for running the HauntBro medallion architecture ETL pipeline with Bronze→Silver and Silver→Gold transformations.

## 📋 Overview

The ETL pipeline implements a three-layer medallion architecture:

- **🥉 Bronze Layer**: Raw, immutable scraped data with audit trails
- **🥈 Silver Layer**: Language-specific processing with chunking and embeddings  
- **🥇 Gold Layer**: Business intelligence metrics and analytics

## 🏗️ Architecture Components

### Core Processing Scripts

⚠️ **IMPORTANT**: Scripts in `etl/processing/scripts/` have implementation issues and should be used with caution:

- `run_bronze_to_silver_etl.py` - **Enhanced Bronze→Silver ETL** with medallion architecture integration
  - Uses SilverProcessor and BronzeProcessor classes
  - Supports test mode and processing limits
  - Integrates with config system and database ORM

- `run_silver_etl.py` - **Legacy Silver Processing Script** ⚠️ **DEPRECATED**
  - Contains direct database operations and hardcoded logic
  - Uses basic chunking without embeddings
  - Missing proper error handling and cost tracking
  - **DO NOT USE** - Use `run_bronze_to_silver_etl.py` instead

- `run_silver_to_gold_etl.py` - **Silver→Gold aggregation** with business metrics
  - Processes silver layer data into business intelligence metrics
  - Includes cross-platform insights and cost analysis
  - Supports date range processing and validation

- `check_etl_health.py` - **Comprehensive health checker** for ETL infrastructure
  - Validates database connectivity and schema
  - Checks Ollama service and required models
  - Tests Docker services and dependencies
  - Generates health reports with recommendations

- `airflow/dags/hauntbro_etl_dag.py` - Airflow orchestration DAG

### Testing & Validation
- `test_etl_pipeline.py` - Comprehensive ETL pipeline testing suite
- `check_etl_health.py` - Infrastructure health checks and Docker validation (also listed above)

### Language Processing Models
- **Chinese**: GPT-4o-mini via OpenAI API with DeepSeek fallback
- **English**: GPT-4o-mini via OpenAI API with LLaMA fallback  
- **Factory Pattern**: Unified language processor factory for extensibility
- **Embeddings**: Multi-model approach with cost optimization
- **RAG Search**: Conversational AI-powered story discovery

## 🚀 Quick Start

### 1. Environment Setup

Ensure your `.env` file contains all required configuration:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hbrawdata
DB_USER=hbadmin  
DB_PASSWORD=your_password

# Ollama Configuration (Docker)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODELS=llama3.2 deepseek-coder

# Optional: OpenAI for embeddings
OPENAI_API_KEY=your_openai_key
```

### 2. Docker Services

Start all required services:

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check specific services
docker-compose logs ollama
docker-compose logs airflow-webserver
```

### 3. Health Check

Validate your environment before running ETL:

```bash
# Comprehensive health check
python etl/processing/scripts/check_etl_health.py --verbose

# Quick essential checks only
python etl/processing/scripts/check_etl_health.py --quick

# Save health report
python etl/processing/scripts/check_etl_health.py --save-report
```

## 🔄 ETL Pipeline Execution

### Bronze → Silver Processing

Transform raw bronze data into processed silver chunks:

```bash
# Test mode (small dataset) - RECOMMENDED APPROACH
python etl/processing/scripts/run_bronze_to_silver_etl.py --test-mode

# Production mode with limit
python etl/processing/scripts/run_bronze_to_silver_etl.py --limit 100

# Full processing (no limit)
python etl/processing/scripts/run_bronze_to_silver_etl.py

# ⚠️ DO NOT USE: Legacy script with issues
# python etl/processing/scripts/run_silver_etl.py
```

**Features:**
- ✅ Automatic language detection (Chinese/English)
- ✅ Factory pattern for language processor extensibility
- ✅ GPT-4o-mini for enhanced text processing with fallbacks
- ✅ Multi-model embedding generation with cost optimization
- ✅ Quality assessment and filtering
- ✅ Real-time progress monitoring
- ✅ Comprehensive error handling and retry logic
- ✅ RAG-powered conversational search API

### Silver → Gold Processing

Aggregate silver data into business intelligence metrics:

```bash
# Test mode (single day)
python etl/processing/scripts/run_silver_to_gold_etl.py --test-mode

# Process specific date
python etl/processing/scripts/run_silver_to_gold_etl.py --single-date 2024-01-15

# Process last 7 days
python etl/processing/scripts/run_silver_to_gold_etl.py --days 7

# Process last 30 days
python etl/processing/scripts/run_silver_to_gold_etl.py --days 30
```

**Features:**
- ✅ Daily metrics aggregation for all platforms
- ✅ Cross-platform comparative analysis (PTT vs Reddit)
- ✅ Business KPIs and performance metrics
- ✅ Cost analysis and optimization recommendations
- ✅ Data quality validation
- ✅ Automated insights generation

## 🤖 RAG Search API

### Conversational Story Discovery

The enhanced search API now includes RAG (Retrieval-Augmented Generation) capabilities:

```bash
# Example RAG queries via API
curl -X POST "http://localhost:8000/api/v1/search/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are common themes in Chinese ghost stories?",
    "language": "auto"
  }'

curl -X POST "http://localhost:8000/api/v1/search/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Can you recommend stories with haunted house elements?",
    "conversation_history": [
      {"type": "question", "content": "What themes do you have?"},
      {"type": "answer", "content": "We have supernatural, psychological horror..."}
    ]
  }'
```

**RAG Features:**
- ✅ Conversational AI responses with source citations  
- ✅ Semantic search with relevance scoring
- ✅ Multi-language support (Chinese/English)
- ✅ Conversation history for context
- ✅ Follow-up question suggestions
- ✅ Confidence scoring for answers

**Available Endpoints:**
- `POST /api/v1/search/ask` - RAG question answering
- `GET /api/v1/search/ask/examples` - Example questions
- `GET /api/v1/search/health` - Service health with RAG status

## 🧪 Testing & Validation

### Comprehensive Test Suite

Run the complete ETL pipeline test suite:

```bash
# First, always run health check
python etl/processing/scripts/check_etl_health.py --verbose

# Full test suite (when available)
python etl/processing/tests/test_etl_pipeline.py

# Quick tests only
python etl/processing/tests/test_etl_pipeline.py --quick

# Test specific layers
python etl/processing/tests/test_etl_pipeline.py --bronze-only
python etl/processing/tests/test_etl_pipeline.py --silver-only  
python etl/processing/tests/test_etl_pipeline.py --gold-only

# Environment setup test only
python etl/processing/tests/test_etl_pipeline.py --environment-only
```

**Test Coverage:**
- ✅ Environment configuration validation
- ✅ Bronze layer ingestion with sample data
- ✅ Silver layer processing with language detection
- ✅ Gold layer aggregation and metrics generation
- ✅ End-to-end pipeline validation
- ✅ Performance and concurrency testing
- ✅ Error handling and recovery testing

## 📅 Airflow Scheduling

### DAG Configuration

The Airflow DAG provides automated scheduling:

- **Schedule**: Daily at 2:00 AM UTC
- **Concurrency**: Maximum 1 active run
- **Retry Logic**: 2-3 retries with exponential backoff
- **Notifications**: Email alerts on failure

### Airflow Web Interface

Access the Airflow web interface:

```bash
# Start Airflow services
docker-compose up -d airflow-webserver airflow-scheduler

# Access web interface
open http://localhost:8080

# Default credentials (if authentication enabled)
# Username: admin
# Password: admin123
```

### Manual DAG Execution

```bash
# Trigger DAG manually
docker exec airflow-webserver airflow dags trigger hauntbro_etl_pipeline

# Check DAG status
docker exec airflow-webserver airflow dags state hauntbro_etl_pipeline

# View task logs
docker exec airflow-webserver airflow tasks log hauntbro_etl_pipeline run_bronze_to_silver_etl
```

## 🔧 Configuration Options

### Model Configuration

Configure language models in `etl/config/config.py`:

```python
@dataclass
class ModelConfig:
    ollama_base_url: str = "http://localhost:11434"
    english_model: str = "llama3.2"
    chinese_model: str = "deepseek-coder"
    temperature: float = 0.3
    top_p: float = 0.9

# Factory pattern usage
from etl.models import LanguageProcessorFactory, process_text

# Auto-detect language and process
result = await process_text(
    text="Your story content here",
    title="Story Title"  
)

# Or specify language explicitly
processor = await LanguageProcessorFactory.create_and_initialize_processor('zh')
result = await processor.process_story(chinese_text, title)
```

### Processing Limits

Adjust processing parameters:

```python
@dataclass
class ChunkingConfig:
    target_chunk_size: int = 512
    max_chunks_per_story: int = 50
    min_quality_score: float = 0.5
    max_chunk_size: int = 768
```

### Database Configuration

Database connection settings:

```python
@dataclass
class DatabaseConfig:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "5432"))
    database: str = os.getenv("DB_NAME", "hauntbro")
    min_connections: int = 5
    max_connections: int = 20
```

## 📊 Monitoring & Analytics

### Processing Statistics

Each ETL script provides comprehensive statistics:

```bash
# Bronze → Silver Statistics
- Stories processed vs skipped vs failed
- Language distribution (Chinese/English/Mixed)
- Quality score distribution
- Processing costs and timing
- Chunk generation metrics

# Silver → Gold Statistics  
- Metrics generated per platform
- Cross-platform insights
- Business KPI calculations
- Data quality validation results
- Cost optimization recommendations
```

### Log Files

Monitor ETL execution through logs:

```bash
# Airflow logs
docker-compose logs -f airflow-scheduler
docker-compose logs -f airflow-webserver

# Ollama model logs
docker-compose logs -f ollama

# Database logs
docker-compose logs -f hauntbro-db
```

## 🚨 Troubleshooting

### Common Issues

1. **Ollama Models Not Available**
   ```bash
   # Check Ollama status
   curl http://localhost:11434/api/tags
   
   # Pull required models
   docker exec ollama ollama pull llama3.2
   docker exec ollama ollama pull deepseek-coder
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connectivity
   python etl/processing/scripts/check_etl_health.py --deps-only
   
   # Test database connection
   docker exec hauntbro-db pg_isready -U postgres
   ```

3. **Memory Issues**
   ```bash
   # Monitor resource usage
   docker stats
   
   # Reduce batch size in scripts
   python etl/processing/scripts/run_bronze_to_silver_etl.py --limit 10
   ```

4. **Permission Issues**
   ```bash
   # Check file permissions
   python etl/processing/scripts/check_etl_health.py --quick
   
   # Fix Docker permissions
   sudo chown -R $(id -u):$(id -g) ./airflow
   ```

### Error Recovery

ETL scripts include comprehensive error handling:

- **Automatic Retries**: Failed tasks retry with exponential backoff
- **Partial Processing**: Continue processing remaining items after failures
- **State Preservation**: Resume from last successful checkpoint
- **Detailed Logging**: Complete error traces for debugging

## 📈 Performance Optimization

### Batch Size Tuning

Optimize performance based on your hardware:

```bash
# Small batch for limited resources
python etl/processing/scripts/run_bronze_to_silver_etl.py --limit 50

# Medium batch for standard hardware  
python etl/processing/scripts/run_bronze_to_silver_etl.py --limit 200

# Large batch for high-performance systems
python etl/processing/scripts/run_bronze_to_silver_etl.py --limit 1000
```

### Concurrent Processing

Adjust concurrency in the processors:

- **Bronze→Silver**: Default 5 concurrent stories
- **Silver→Gold**: Default 3 concurrent date ranges
- **Model Processing**: Controlled by Ollama queue management

### Cost Optimization

Minimize processing costs:

- **Free Models First**: Sentence Transformers before OpenAI
- **Batch Processing**: Group similar content types
- **Quality Filtering**: Skip low-quality content early
- **Caching**: Reuse embeddings for similar content

## 🔮 Advanced Usage

### Custom Processing Workflows

Create custom ETL workflows:

```python
# Custom Bronze→Silver with specific language
from etl.medallion.silver_processor import SilverProcessor

processor = SilverProcessor()
await processor.initialize()

# Process only Chinese stories
stories = await processor.get_unprocessed_stories(limit=100)
chinese_stories = [s for s in stories if detect_language(s['content']) == 'zh']

for story in chinese_stories:
    result = await processor.process_story(story, 'custom_run')
    print(f"Processed: {result.chunks_generated} chunks")
```

### Integration with External Systems

Extend the pipeline for external integrations:

```python
# Custom notification system
def send_completion_notification(stats):
    # Integrate with Slack, Discord, etc.
    pass

# Custom metric export
def export_metrics_to_dashboard(gold_metrics):
    # Export to Grafana, PowerBI, etc.
    pass
```

## 📚 Additional Resources

- **Project Documentation**: `docs/CLAUDE.md`
- **Database Schema**: `hauntbro_schema.sql`
- **Docker Configuration**: `docker-compose.yml`
- **Airflow Configuration**: `airflow/config/airflow.cfg`

## 🤝 Support

For issues or questions:

1. Check health status: `python etl/processing/scripts/check_etl_health.py`
2. Run test suite: `python etl/processing/tests/test_etl_pipeline.py` (when available)
3. Review logs in Docker containers
4. Check Airflow web interface for DAG status

**Script Summary:**
- ✅ **Use**: `run_bronze_to_silver_etl.py` for Bronze→Silver processing
- ✅ **Use**: `run_silver_to_gold_etl.py` for Silver→Gold processing  
- ✅ **Use**: `check_etl_health.py` for system validation
- ❌ **Avoid**: `run_silver_etl.py` - deprecated with implementation issues

---

**🎉 Happy ETL Processing!** 

The HauntBro ETL pipeline is designed for scalability, reliability, and comprehensive monitoring. Follow this guide to efficiently process ghost stories from bronze raw data to gold business insights.