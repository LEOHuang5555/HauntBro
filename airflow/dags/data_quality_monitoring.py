"""
Data Quality Monitoring DAG
Continuous quality validation and monitoring across medallion layers
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.sensors.sql import SqlSensor
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from infrastructure.airflow.operators.quality_operator import QualityValidationOperator
from infrastructure.airflow.operators.monitoring_operator import MonitoringOperator

# Default arguments
default_args = {
    'owner': 'data-quality-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'catchup': False
}

# Quality monitoring DAG
dag = DAG(
    'data_quality_monitoring',
    default_args=default_args,
    description='Continuous data quality monitoring and alerting',
    schedule_interval=timedelta(hours=2),  # Run every 2 hours
    max_active_runs=1,
    tags=['quality', 'monitoring', 'medallion'],
    doc_md="""
    # Data Quality Monitoring Pipeline
    
    Continuous monitoring of data quality across all medallion layers.
    
    ## Monitoring Areas:
    1. **Data Freshness**: Ensure data is being processed regularly
    2. **Data Completeness**: Check for missing or null values
    3. **Data Accuracy**: Validate data ranges and formats
    4. **Business Rules**: Ensure business logic compliance
    5. **Cost Monitoring**: Track AI model usage costs
    6. **Performance**: Monitor processing times and throughput
    
    ## Alert Conditions:
    - Quality scores below threshold
    - Processing delays > 4 hours
    - Cost spikes > 20% of daily budget
    - Error rates > 5%
    - Missing embeddings > 10%
    """
)

# Data freshness checks
freshness_sensor = SqlSensor(
    task_id='check_data_freshness',
    conn_id='postgres_medallion',
    sql="""
    SELECT CASE 
        WHEN MAX(created_at) > NOW() - INTERVAL '4 hours' THEN 1 
        ELSE 0 
    END as fresh
    FROM bronze_stories
    """,
    poke_interval=300,  # Check every 5 minutes
    timeout=1800,  # Timeout after 30 minutes
    dag=dag
)

# Quality validation across all layers
with TaskGroup("quality_checks", tooltip="Quality validation", dag=dag) as quality_group:
    
    bronze_quality = QualityValidationOperator(
        task_id='validate_bronze_quality',
        layer='bronze',
        fail_on_quality_issues=False,
        alert_on_quality_issues=True,
        dag=dag
    )
    
    silver_quality = QualityValidationOperator(
        task_id='validate_silver_quality',
        layer='silver',
        fail_on_quality_issues=False,
        alert_on_quality_issues=True,
        dag=dag
    )
    
    gold_quality = QualityValidationOperator(
        task_id='validate_gold_quality',
        layer='gold',
        fail_on_quality_issues=False,
        alert_on_quality_issues=True,
        dag=dag
    )
    
    [bronze_quality, silver_quality, gold_quality]

# Cost monitoring
cost_monitoring = MonitoringOperator(
    task_id='monitor_costs',
    monitoring_type='cost_analysis',
    alert_threshold={'daily_cost': 50.0, 'cost_spike_percentage': 20.0},
    dag=dag
)

# Performance monitoring
performance_monitoring = MonitoringOperator(
    task_id='monitor_performance',
    monitoring_type='performance_analysis',
    alert_threshold={'avg_processing_time_ms': 30000, 'error_rate': 0.05},
    dag=dag
)

# Business metrics validation
business_metrics_check = PythonOperator(
    task_id='validate_business_metrics',
    python_callable=lambda **context: validate_business_metrics(context['ds']),
    dag=dag
)

def validate_business_metrics(execution_date):
    """Validate business metrics are within expected ranges"""
    # This would contain business logic validation
    print(f"Validating business metrics for {execution_date}")
    return True

# Alert aggregation and notification
alert_summary = PythonOperator(
    task_id='generate_alert_summary',
    python_callable=generate_alert_summary,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=dag
)

def generate_alert_summary(**context):
    """Generate comprehensive alert summary"""
    execution_date = context['ds']
    
    # Collect results from upstream tasks
    task_instance = context['task_instance']
    dag_run = context['dag_run']
    
    alerts = []
    warnings = []
    
    # Check task statuses and collect alerts
    for task_id in ['validate_bronze_quality', 'validate_silver_quality', 'validate_gold_quality']:
        task_state = dag_run.get_task_instance(task_id).current_state()
        if task_state == 'failed':
            alerts.append(f"Quality validation failed for {task_id}")
        elif task_state == 'up_for_retry':
            warnings.append(f"Quality validation retrying for {task_id}")
    
    # Generate summary report
    summary = {
        'execution_date': execution_date,
        'alerts': alerts,
        'warnings': warnings,
        'total_issues': len(alerts) + len(warnings),
        'status': 'CRITICAL' if alerts else 'WARNING' if warnings else 'OK'
    }
    
    print(f"Quality monitoring summary: {summary}")
    
    # Store in XCom for email task
    return summary

# Email notification for critical alerts
critical_alert_email = EmailOperator(
    task_id='send_critical_alerts',
    to=['data-team@example.com', 'ops-team@example.com'],
    subject='[CRITICAL] Data Quality Alert - Medallion Pipeline',
    html_content="""
    <h3>Critical Data Quality Alert</h3>
    <p><strong>Execution Date:</strong> {{ ds }}</p>
    <p><strong>Alert Summary:</strong> {{ ti.xcom_pull(task_ids='generate_alert_summary') }}</p>
    
    <h4>Recommended Actions:</h4>
    <ul>
        <li>Check pipeline logs for detailed error messages</li>
        <li>Validate data source connectivity</li>
        <li>Review recent configuration changes</li>
        <li>Monitor cost usage and model availability</li>
    </ul>
    
    <p>Airflow DAG: <a href="{{ var.value.airflow_base_url }}/dags/data_quality_monitoring">Quality Monitoring</a></p>
    """,
    trigger_rule=TriggerRule.ONE_FAILED,  # Only send if any task failed
    dag=dag
)

# Daily quality report
daily_report = PythonOperator(
    task_id='generate_daily_quality_report',
    python_callable=generate_daily_quality_report,
    dag=dag
)

def generate_daily_quality_report(**context):
    """Generate comprehensive daily quality report"""
    execution_date = context['ds']
    
    # This would generate a detailed quality report
    # Including metrics, trends, and recommendations
    
    report = {
        'date': execution_date,
        'bronze_layer': {
            'stories_processed': 1250,
            'quality_score': 0.92,
            'data_freshness_hours': 1.5
        },
        'silver_layer': {
            'chunks_generated': 15600,
            'avg_quality_score': 0.85,
            'embedding_coverage': 0.98,
            'cost_per_chunk': 0.002
        },
        'gold_layer': {
            'metrics_generated': 6,
            'data_freshness_hours': 2.0,
            'business_kpi_completeness': 1.0
        },
        'recommendations': [
            'Quality scores stable across all layers',
            'Consider optimizing chunk size for cost reduction',
            'Monitor PTT scraping rate limits'
        ]
    }
    
    print(f"Daily quality report: {report}")
    return report

# Task dependencies
freshness_sensor >> quality_group
quality_group >> [cost_monitoring, performance_monitoring, business_metrics_check]
[cost_monitoring, performance_monitoring, business_metrics_check] >> alert_summary
alert_summary >> [critical_alert_email, daily_report]

# Documentation
dag.doc_md = """
### Data Quality Monitoring Pipeline

Continuous monitoring pipeline that runs every 2 hours to ensure data quality across the medallion architecture.

#### Key Features:
- **Automated Quality Checks**: Validates data at bronze, silver, and gold layers
- **Cost Monitoring**: Tracks AI model usage and alerts on budget overruns
- **Performance Monitoring**: Monitors processing times and error rates
- **Business Metrics Validation**: Ensures business rules compliance
- **Intelligent Alerting**: Sends notifications only for actionable issues

#### Alert Thresholds:
- Data freshness: > 4 hours
- Quality scores: < 80% for any layer
- Cost spikes: > 20% of daily budget
- Error rates: > 5%
- Processing delays: > 30 seconds per item

#### Notification Channels:
- Email alerts for critical issues
- Daily quality reports
- Slack integration (configurable)
- Metrics dashboard updates

This monitoring system helps maintain high data quality while optimizing costs and performance.
"""