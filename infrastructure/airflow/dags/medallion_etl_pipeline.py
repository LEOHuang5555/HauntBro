"""
Medallion ETL Pipeline DAG
Main orchestration for Bronze → Silver → Gold data processing
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Import custom operators
from infrastructure.airflow.operators.bronze_operator import BronzeProcessorOperator
from infrastructure.airflow.operators.silver_operator import SilverProcessorOperator
from infrastructure.airflow.operators.gold_operator import GoldProcessorOperator
from infrastructure.airflow.operators.quality_operator import QualityValidationOperator

# Default arguments
default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'max_active_runs': 1,
    'catchup': False
}

# DAG definition
dag = DAG(
    'medallion_etl_pipeline',
    default_args=default_args,
    description='Complete ETL pipeline for ghost story medallion architecture',
    schedule_interval='@daily',  # Run daily at midnight
    max_active_runs=1,
    tags=['medallion', 'etl', 'ghost-stories'],
    doc_md="""
    # Medallion ETL Pipeline
    
    Complete end-to-end data processing pipeline for the ghost story search engine.
    
    ## Process Flow:
    1. **Bronze Layer**: Ingest raw data from Reddit and PTT
    2. **Quality Gate 1**: Validate bronze data quality
    3. **Silver Layer**: Clean, chunk, and generate embeddings
    4. **Quality Gate 2**: Validate silver data quality
    5. **Gold Layer**: Generate business metrics and analytics
    6. **Quality Gate 3**: Validate gold metrics
    7. **Monitoring**: Update metrics and send alerts
    
    ## Data Sources:
    - Reddit /r/nosleep and /r/ghoststories
    - PTT supernatural boards
    
    ## Models Used:
    - DeepSeek (Chinese text processing)
    - LLaMA (English text processing) 
    - OpenAI Embeddings (vector generation)
    """
)

# Bronze Layer Processing
with TaskGroup("bronze_layer", tooltip="Raw data ingestion", dag=dag) as bronze_group:
    
    # Reddit data processing
    bronze_reddit = BronzeProcessorOperator(
        task_id='process_reddit_stories',
        source_platform='reddit',
        batch_size=100,
        dag=dag
    )
    
    # PTT data processing
    bronze_ptt = BronzeProcessorOperator(
        task_id='process_ptt_stories',
        source_platform='ptt',
        batch_size=100,
        dag=dag
    )
    
    # Quality validation for bronze layer
    bronze_quality = QualityValidationOperator(
        task_id='validate_bronze_quality',
        layer='bronze',
        fail_on_quality_issues=True,
        dag=dag
    )
    
    [bronze_reddit, bronze_ptt] >> bronze_quality

# Silver Layer Processing
with TaskGroup("silver_layer", tooltip="Language processing and embeddings", dag=dag) as silver_group:
    
    # Multi-language processing
    silver_processing = SilverProcessorOperator(
        task_id='process_silver_chunks',
        batch_size=50,
        quality_threshold=0.5,
        dag=dag
    )
    
    # Quality validation for silver layer
    silver_quality = QualityValidationOperator(
        task_id='validate_silver_quality',
        layer='silver',
        fail_on_quality_issues=True,
        dag=dag
    )
    
    silver_processing >> silver_quality

# Gold Layer Processing
with TaskGroup("gold_layer", tooltip="Business intelligence metrics", dag=dag) as gold_group:
    
    # Generate business metrics
    gold_processing = GoldProcessorOperator(
        task_id='generate_gold_metrics',
        target_date="{{ ds }}",
        platforms=['ptt', 'reddit', 'combined'],
        dag=dag
    )
    
    # Quality validation for gold layer
    gold_quality = QualityValidationOperator(
        task_id='validate_gold_quality',
        layer='gold',
        fail_on_quality_issues=False,  # Don't fail pipeline on gold quality issues
        dag=dag
    )
    
    gold_processing >> gold_quality

# Monitoring and cleanup
monitoring_task = PythonOperator(
    task_id='update_monitoring_metrics',
    python_callable=lambda **context: print(f"Pipeline completed for {context['ds']}"),
    dag=dag
)

# Task dependencies
bronze_group >> silver_group >> gold_group >> monitoring_task

# Add documentation
dag.doc_md = """
### Medallion ETL Pipeline

This DAG implements the complete medallion architecture for the ghost story search engine:

#### Bronze Layer (Raw Data)
- Ingests raw stories from Reddit and PTT
- Preserves original content without modification
- Validates basic data structure

#### Silver Layer (Processed Data) 
- Language detection and routing
- Content cleaning and chunking
- Multi-language model processing (DeepSeek/LLaMA)
- Embedding generation with cost optimization

#### Gold Layer (Business Intelligence)
- Daily metrics aggregation
- Cross-platform analytics
- Business KPI calculation
- User engagement metrics

#### Quality Gates
- Great Expectations validation at each layer
- Configurable quality thresholds
- Automatic retry on transient failures

#### Monitoring
- Real-time metrics tracking
- Cost optimization analysis
- Performance monitoring
- Alert generation for failures

The pipeline is designed to handle large volumes of multilingual content with cost-optimized AI model usage.
"""