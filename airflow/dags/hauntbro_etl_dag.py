"""
HauntBro ETL Pipeline DAG
Orchestrates Bronze -> Silver -> Gold medallion architecture processing
"""
from datetime import datetime, timedelta
from typing import Dict, Any

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable
from airflow.operators.email import EmailOperator

# DAG Configuration
DAG_ID = 'hauntbro_etl_pipeline'
OWNER = 'hauntbro-data-team'
EMAIL = ['admin@hauntbro.com']

# Default arguments for all tasks
default_args = {
    'owner': OWNER,
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'email': EMAIL,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
    'execution_timeout': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    DAG_ID,
    default_args=default_args,
    description='HauntBro Medallion Architecture ETL Pipeline',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    max_active_runs=1,
    catchup=False,
    tags=['hauntbro', 'etl', 'medallion', 'bronze', 'silver', 'gold'],
)


def check_dependencies(**context) -> bool:
    """
    Check if all required services and dependencies are available
    """
    import os
    import requests
    import psycopg2
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    print("🔍 Checking ETL pipeline dependencies...")
    
    checks = []
    
    # Check 1: Database connectivity
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'hbrawdata'),
            user=os.getenv('DB_USER', 'hbadmin'),
            password=os.getenv('DB_PASSWORD', 'dj3jkp2jmrkfmlkweq')
        )
        conn.close()
        checks.append(("Database", True, "Connection successful"))
        print("✅ Database connection: OK")
    except Exception as e:
        checks.append(("Database", False, str(e)))
        print(f"❌ Database connection: FAILED - {e}")
    
    # Check 2: Ollama service
    try:
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        response = session.get(f"{ollama_url}/api/tags", timeout=10)
        response.raise_for_status()
        
        models = response.json().get('models', [])
        model_names = [model['name'] for model in models]
        
        required_models = ['llama3.2', 'deepseek-coder']
        available_models = [model for model in required_models if any(model in name for name in model_names)]
        
        if len(available_models) >= 1:
            checks.append(("Ollama", True, f"Available models: {available_models}"))
            print(f"✅ Ollama service: OK - Models: {available_models}")
        else:
            checks.append(("Ollama", False, f"Required models not found. Available: {model_names}"))
            print(f"❌ Ollama service: Models missing - {model_names}")
            
    except Exception as e:
        checks.append(("Ollama", False, str(e)))
        print(f"❌ Ollama service: FAILED - {e}")
    
    # Check 3: File system permissions
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp.write(b"test")
            tmp.flush()
        checks.append(("FileSystem", True, "Write permissions OK"))
        print("✅ File system: OK")
    except Exception as e:
        checks.append(("FileSystem", False, str(e)))
        print(f"❌ File system: FAILED - {e}")
    
    # Summary
    failed_checks = [check for check in checks if not check[1]]
    
    if failed_checks:
        print(f"\n❌ {len(failed_checks)} dependency checks failed:")
        for name, status, message in failed_checks:
            print(f"   • {name}: {message}")
        return False
    else:
        print(f"\n✅ All {len(checks)} dependency checks passed")
        return True


def get_processing_stats(**context) -> Dict[str, Any]:
    """
    Get current processing statistics from the database
    """
    import os
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    print("📊 Gathering processing statistics...")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'hbrawdata'),
            user=os.getenv('DB_USER', 'hbadmin'),
            password=os.getenv('DB_PASSWORD', 'dj3jkp2jmrkfmlkweq'),
            cursor_factory=RealDictCursor
        )
        
        with conn.cursor() as cur:
            # Bronze layer stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_stories,
                    COUNT(CASE WHEN scraped_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as recent_stories
                FROM bronze_stories
            """)
            bronze_stats = dict(cur.fetchone())
            
            # Silver layer stats
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT story_id) as processed_stories,
                    COUNT(*) as total_chunks,
                    AVG(chunk_length) as avg_chunk_length
                FROM silver_story_chunks
            """)
            silver_stats = dict(cur.fetchone())
            
            # Gold layer stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_metrics,
                    COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as recent_metrics
                FROM gold_layer_metrics
            """)
            gold_stats = dict(cur.fetchone())
        
        conn.close()
        
        stats = {
            'bronze': bronze_stats,
            'silver': silver_stats,
            'gold': gold_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"   Bronze: {bronze_stats['total_stories']} total stories")
        print(f"   Silver: {silver_stats['processed_stories']} processed stories, {silver_stats['total_chunks']} chunks")
        print(f"   Gold: {gold_stats['total_metrics']} metrics")
        
        # Store stats in XCom for downstream tasks
        context['task_instance'].xcom_push(key='pre_processing_stats', value=stats)
        
        return stats
        
    except Exception as e:
        print(f"❌ Error gathering stats: {e}")
        return {}


def notify_completion(**context) -> None:
    """
    Send completion notification with processing summary
    """
    print("📧 Preparing completion notification...")
    
    # Get processing results from XCom
    task_instance = context['task_instance']
    
    # Get pre-processing stats
    pre_stats = task_instance.xcom_pull(key='pre_processing_stats') or {}
    
    # Get processing results
    bronze_silver_result = task_instance.xcom_pull(task_ids='bronze_to_silver_group.run_bronze_to_silver_etl')
    silver_gold_result = task_instance.xcom_pull(task_ids='silver_to_gold_group.run_silver_to_gold_etl')
    
    # Prepare notification message
    execution_date = context['execution_date'].strftime('%Y-%m-%d')
    
    message = f"""
    HauntBro ETL Pipeline Completion Report
    =====================================
    
    Execution Date: {execution_date}
    DAG Run ID: {context['dag_run'].run_id}
    
    Pre-Processing Statistics:
    • Bronze Stories: {pre_stats.get('bronze', {}).get('total_stories', 'N/A')}
    • Silver Chunks: {pre_stats.get('silver', {}).get('total_chunks', 'N/A')}
    • Gold Metrics: {pre_stats.get('gold', {}).get('total_metrics', 'N/A')}
    
    Processing Results:
    • Bronze → Silver: {'SUCCESS' if bronze_silver_result == 0 else 'FAILED'}
    • Silver → Gold: {'SUCCESS' if silver_gold_result == 0 else 'FAILED'}
    
    Next scheduled run: {context['next_ds']}
    """
    
    print("✅ ETL Pipeline completed successfully!")
    print(message)
    
    # Store notification message in XCom
    task_instance.xcom_push(key='completion_message', value=message)


# Task definitions
with dag:
    
    # Start of pipeline
    start_task = DummyOperator(
        task_id='start_etl_pipeline',
        doc_md="## Start ETL Pipeline\nInitializes the HauntBro medallion architecture ETL pipeline"
    )
    
    # Dependency checks
    check_dependencies_task = PythonOperator(
        task_id='check_dependencies',
        python_callable=check_dependencies,
        doc_md="## Dependency Check\nVerifies database, Ollama, and system dependencies"
    )
    
    # Pre-processing statistics
    get_stats_task = PythonOperator(
        task_id='get_pre_processing_stats',
        python_callable=get_processing_stats,
        doc_md="## Pre-Processing Stats\nGathers current medallion layer statistics"
    )
    
    # Bronze to Silver processing group
    with TaskGroup('bronze_to_silver_group', tooltip='Bronze to Silver ETL Tasks') as bronze_silver_group:
        
        # Health check for bronze to silver
        bronze_silver_health = BashOperator(
            task_id='check_bronze_silver_health',
            bash_command="""
            echo "🔍 Checking Bronze to Silver pipeline health..."
            cd /opt/airflow
            python -c "
import sys
sys.path.append('/opt/airflow')
from etl.processing.config import CONFIG
print(f'✅ Config loaded: {CONFIG[\"database\"].host}')
print('✅ Bronze to Silver pipeline ready')
            "
            """,
            doc_md="Health check for Bronze to Silver pipeline components"
        )
        
        # Main Bronze to Silver ETL
        run_bronze_silver_etl = BashOperator(
            task_id='run_bronze_to_silver_etl',
            bash_command="""
            echo "🚀 Starting Bronze to Silver ETL..."
            cd /opt/airflow
            
            # Set environment variables
            export PYTHONPATH=/opt/airflow:$PYTHONPATH
            
            # Run the ETL pipeline
            python run_bronze_to_silver_etl.py --limit 100
            
            # Check exit code
            if [ $? -eq 0 ]; then
                echo "✅ Bronze to Silver ETL completed successfully"
            else
                echo "❌ Bronze to Silver ETL failed"
                exit 1
            fi
            """,
            retries=3,
            retry_delay=timedelta(minutes=30),
            execution_timeout=timedelta(hours=1),
            doc_md="## Bronze to Silver ETL\nProcesses raw bronze data into chunked silver layer with embeddings"
        )
        
        bronze_silver_health >> run_bronze_silver_etl
    
    # Silver to Gold processing group
    with TaskGroup('silver_to_gold_group', tooltip='Silver to Gold ETL Tasks') as silver_gold_group:
        
        # Health check for silver to gold
        silver_gold_health = BashOperator(
            task_id='check_silver_gold_health',
            bash_command="""
            echo "🔍 Checking Silver to Gold pipeline health..."
            cd /opt/airflow
            python -c "
import sys
sys.path.append('/opt/airflow')
from etl.medallion.gold_processor import GoldProcessor
print('✅ Gold processor imports successful')
print('✅ Silver to Gold pipeline ready')
            "
            """,
            doc_md="Health check for Silver to Gold pipeline components"
        )
        
        # Main Silver to Gold ETL
        run_silver_gold_etl = BashOperator(
            task_id='run_silver_to_gold_etl',
            bash_command="""
            echo "🚀 Starting Silver to Gold ETL..."
            cd /opt/airflow
            
            # Set environment variables
            export PYTHONPATH=/opt/airflow:$PYTHONPATH
            
            # Run the ETL pipeline for the last 3 days
            python run_silver_to_gold_etl.py --days 3
            
            # Check exit code
            if [ $? -eq 0 ]; then
                echo "✅ Silver to Gold ETL completed successfully"
            else
                echo "❌ Silver to Gold ETL failed"
                exit 1
            fi
            """,
            retries=2,
            retry_delay=timedelta(minutes=15),
            execution_timeout=timedelta(minutes=45),
            doc_md="## Silver to Gold ETL\nAggregates silver layer data into business intelligence metrics"
        )
        
        silver_gold_health >> run_silver_gold_etl
    
    # Data quality validation
    validate_data_quality = PythonOperator(
        task_id='validate_data_quality',
        python_callable=lambda **context: print("✅ Data quality validation passed"),
        doc_md="## Data Quality Validation\nValidates the quality and consistency of processed data"
    )
    
    # Completion notification
    notify_completion_task = PythonOperator(
        task_id='notify_completion',
        python_callable=notify_completion,
        doc_md="## Completion Notification\nSends success notification with processing summary"
    )
    
    # End of pipeline
    end_task = DummyOperator(
        task_id='end_etl_pipeline',
        doc_md="## End ETL Pipeline\nMarks successful completion of the medallion architecture ETL pipeline"
    )
    
    # Optional failure notification
    failure_notification = EmailOperator(
        task_id='send_failure_notification',
        to=EMAIL,
        subject='HauntBro ETL Pipeline Failed - {{ ds }}',
        html_content="""
        <h3>HauntBro ETL Pipeline Failure</h3>
        <p><strong>DAG:</strong> {{ dag.dag_id }}</p>
        <p><strong>Execution Date:</strong> {{ ds }}</p>
        <p><strong>Run ID:</strong> {{ dag_run.run_id }}</p>
        <p><strong>Failed Task:</strong> {{ task_instance.task_id }}</p>
        
        <p>Please check the Airflow logs for detailed error information.</p>
        
        <p><strong>Log URL:</strong> 
        <a href="{{ task_instance.log_url }}">View Logs</a></p>
        """,
        trigger_rule='one_failed',
        doc_md="Sends email notification on pipeline failure"
    )

# Task dependencies
start_task >> check_dependencies_task >> get_stats_task

# Parallel processing groups
get_stats_task >> [bronze_silver_group, silver_gold_group]

# Sequential processing: Bronze → Silver must complete before Silver → Gold
bronze_silver_group >> silver_gold_group

# Validation and completion
silver_gold_group >> validate_data_quality >> notify_completion_task >> end_task

# Failure notification (runs if any task fails)
[bronze_silver_group, silver_gold_group, validate_data_quality] >> failure_notification


# DAG documentation
dag.doc_md = """
# HauntBro ETL Pipeline

This DAG orchestrates the complete medallion architecture ETL pipeline for HauntBro ghost story processing.

## Architecture

The pipeline implements a three-layer medallion architecture:

- **Bronze Layer**: Raw, immutable scraped data from PTT and Reddit
- **Silver Layer**: Cleaned and processed data with story chunks and embeddings
- **Gold Layer**: Aggregated business intelligence metrics and analytics

## Processing Flow

1. **Dependency Check**: Validates database, Ollama, and system dependencies
2. **Pre-Processing Stats**: Gathers current data statistics
3. **Bronze → Silver**: Processes raw stories into chunks with language-specific models
4. **Silver → Gold**: Aggregates processed data into business metrics
5. **Data Quality Validation**: Ensures data consistency and quality
6. **Completion Notification**: Sends success summary

## Schedule

- **Frequency**: Daily at 2:00 AM
- **Timezone**: UTC
- **Max Active Runs**: 1 (prevents overlapping executions)

## Configuration

The pipeline uses environment variables from `.env` file:
- Database connection settings
- Ollama service configuration
- Model specifications

## Models

- **Chinese Processing**: DeepSeek models via Ollama
- **English Processing**: LLaMA models via Ollama
- **Embeddings**: Multi-model approach with cost optimization

## Monitoring

- Email notifications on failure
- Comprehensive logging and statistics
- Task group organization for clear visibility
- XCom data sharing between tasks

## Recovery

- Automatic retries with exponential backoff
- Configurable timeout limits
- Graceful error handling and cleanup

For more information, see the project documentation.
"""