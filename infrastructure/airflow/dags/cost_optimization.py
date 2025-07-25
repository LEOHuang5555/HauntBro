"""
Cost Optimization DAG
Monitors and optimizes AI model usage costs across the medallion pipeline
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.utils.task_group import TaskGroup
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from infrastructure.airflow.operators.cost_operator import CostAnalysisOperator
from infrastructure.airflow.operators.optimization_operator import ModelOptimizationOperator

# Default arguments
default_args = {
    'owner': 'cost-optimization-team',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'catchup': False
}

# Cost optimization DAG
dag = DAG(
    'cost_optimization',
    default_args=default_args,
    description='AI model cost optimization and budget monitoring',
    schedule_interval='0 */6 * * *',  # Run every 6 hours
    max_active_runs=1,
    tags=['cost', 'optimization', 'ai-models'],
    doc_md="""
    # Cost Optimization Pipeline
    
    Monitors and optimizes AI model usage costs across the medallion architecture.
    
    ## Optimization Areas:
    1. **Model Selection**: Choose most cost-effective models per use case
    2. **Batch Optimization**: Optimize batch sizes for cost efficiency
    3. **Quality vs Cost**: Balance quality requirements with cost constraints
    4. **Usage Analytics**: Track cost trends and predict budget needs
    5. **Alternative Models**: Evaluate free/cheaper model alternatives
    
    ## Cost Categories:
    - OpenAI Embedding API calls
    - DeepSeek Chinese processing
    - LLaMA English processing
    - Compute costs for local models
    
    ## Budget Alerts:
    - Daily budget threshold: $50
    - Weekly budget threshold: $300
    - Monthly budget threshold: $1000
    """
)

# Cost analysis and monitoring
with TaskGroup("cost_analysis", tooltip="Cost monitoring and analysis", dag=dag) as cost_group:
    
    # Analyze current costs
    analyze_costs = CostAnalysisOperator(
        task_id='analyze_current_costs',
        analysis_period='last_24_hours',
        include_predictions=True,
        dag=dag
    )
    
    # Budget monitoring
    budget_check = PythonOperator(
        task_id='check_budget_status',
        python_callable=check_budget_status,
        dag=dag
    )
    
    # Cost trend analysis
    trend_analysis = PythonOperator(
        task_id='analyze_cost_trends',
        python_callable=analyze_cost_trends,
        dag=dag
    )
    
    analyze_costs >> [budget_check, trend_analysis]

def check_budget_status(**context):
    """Check current budget usage against thresholds"""
    execution_date = context['ds']
    
    # Mock budget data - in reality would query cost tracking database
    daily_budget = 50.0
    weekly_budget = 300.0
    monthly_budget = 1000.0
    
    # Current usage (would be retrieved from database)
    current_daily_usage = 32.45
    current_weekly_usage = 186.20
    current_monthly_usage = 567.80
    
    budget_status = {
        'date': execution_date,
        'daily': {
            'budget': daily_budget,
            'used': current_daily_usage,
            'percentage': (current_daily_usage / daily_budget) * 100,
            'remaining': daily_budget - current_daily_usage,
            'alert': current_daily_usage > daily_budget * 0.8
        },
        'weekly': {
            'budget': weekly_budget,
            'used': current_weekly_usage,
            'percentage': (current_weekly_usage / weekly_budget) * 100,
            'remaining': weekly_budget - current_weekly_usage,
            'alert': current_weekly_usage > weekly_budget * 0.8
        },
        'monthly': {
            'budget': monthly_budget,
            'used': current_monthly_usage,
            'percentage': (current_monthly_usage / monthly_budget) * 100,
            'remaining': monthly_budget - current_monthly_usage,
            'alert': current_monthly_usage > monthly_budget * 0.8
        }
    }
    
    # Log budget status
    print(f"Budget Status: {budget_status}")
    
    # Check for alerts
    alerts = []
    if budget_status['daily']['alert']:
        alerts.append(f"Daily budget alert: {budget_status['daily']['percentage']:.1f}% used")
    if budget_status['weekly']['alert']:
        alerts.append(f"Weekly budget alert: {budget_status['weekly']['percentage']:.1f}% used")
    if budget_status['monthly']['alert']:
        alerts.append(f"Monthly budget alert: {budget_status['monthly']['percentage']:.1f}% used")
    
    if alerts:
        print(f"BUDGET ALERTS: {alerts}")
    
    return budget_status

def analyze_cost_trends(**context):
    """Analyze cost trends and generate recommendations"""
    execution_date = context['ds']
    
    # Mock trend data - would analyze historical costs
    trends = {
        'date': execution_date,
        'cost_trends': {
            'openai_embeddings': {
                'daily_average': 25.30,
                'trend': 'increasing',
                'change_percentage': 12.5,
                'recommendation': 'Consider using sentence transformers for non-critical embeddings'
            },
            'deepseek_processing': {
                'daily_average': 8.45,
                'trend': 'stable',
                'change_percentage': 2.1,
                'recommendation': 'Cost stable - continue current usage'
            },
            'llama_processing': {
                'daily_average': 6.20,
                'trend': 'decreasing',
                'change_percentage': -5.8,
                'recommendation': 'Good optimization - maintain current settings'
            }
        },
        'optimization_opportunities': [
            'Switch 30% of embeddings to sentence transformers: Save $8-12/day',
            'Optimize chunk sizes: Potential 15% cost reduction',
            'Batch processing improvements: Reduce API calls by 20%'
        ],
        'predicted_monthly_cost': 890.50,
        'budget_variance': -109.50  # Under budget
    }
    
    print(f"Cost Trends Analysis: {trends}")
    return trends

# Model optimization
with TaskGroup("model_optimization", tooltip="Model usage optimization", dag=dag) as optimization_group:
    
    # Optimize embedding strategy
    optimize_embeddings = ModelOptimizationOperator(
        task_id='optimize_embedding_strategy',
        optimization_type='embedding_cost',
        target_savings_percentage=20,
        dag=dag
    )
    
    # Optimize model selection
    optimize_models = ModelOptimizationOperator(
        task_id='optimize_model_selection',
        optimization_type='model_efficiency',
        quality_threshold=0.8,
        dag=dag
    )
    
    # Batch size optimization
    optimize_batching = PythonOperator(
        task_id='optimize_batch_sizes',
        python_callable=optimize_batch_sizes,
        dag=dag
    )
    
    [optimize_embeddings, optimize_models, optimize_batching]

def optimize_batch_sizes(**context):
    """Analyze and optimize batch sizes for cost efficiency"""
    execution_date = context['ds']
    
    # Mock optimization analysis
    optimization_results = {
        'date': execution_date,
        'current_settings': {
            'bronze_batch_size': 100,
            'silver_batch_size': 50,
            'embedding_batch_size': 32
        },
        'recommended_settings': {
            'bronze_batch_size': 150,  # Increase for better throughput
            'silver_batch_size': 75,   # Increase for cost efficiency
            'embedding_batch_size': 50  # Increase for API cost optimization
        },
        'expected_improvements': {
            'cost_reduction_percentage': 15,
            'processing_time_reduction': 12,
            'api_calls_reduction': 25
        },
        'implementation_risk': 'low',
        'recommended_action': 'implement_gradually'
    }
    
    print(f"Batch Optimization Results: {optimization_results}")
    return optimization_results

# Cost reporting and recommendations
cost_report = PythonOperator(
    task_id='generate_cost_report',
    python_callable=generate_cost_report,
    dag=dag
)

def generate_cost_report(**context):
    """Generate comprehensive cost report with recommendations"""
    execution_date = context['ds']
    
    # Aggregate data from previous tasks
    task_instance = context['task_instance']
    
    # In a real implementation, would pull data from previous tasks
    cost_report = {
        'date': execution_date,
        'executive_summary': {
            'total_daily_cost': 42.95,
            'budget_utilization': 85.9,
            'trend': 'increasing',
            'savings_opportunities': 18.5
        },
        'cost_breakdown': {
            'openai_embeddings': {'cost': 25.30, 'percentage': 58.9},
            'deepseek_chinese': {'cost': 8.45, 'percentage': 19.7},
            'llama_english': {'cost': 6.20, 'percentage': 14.4},
            'infrastructure': {'cost': 3.00, 'percentage': 7.0}
        },
        'recommendations': [
            {
                'priority': 'high',
                'action': 'Implement sentence transformer fallback',
                'savings': '$8-12/day',
                'effort': 'medium'
            },
            {
                'priority': 'medium',
                'action': 'Optimize batch sizes',
                'savings': '$6-8/day',
                'effort': 'low'
            },
            {
                'priority': 'low',
                'action': 'Evaluate alternative embedding models',
                'savings': '$10-15/day',
                'effort': 'high'
            }
        ],
        'quality_impact': 'minimal',
        'implementation_timeline': '2-4 weeks'
    }
    
    print(f"Cost Report Generated: {cost_report}")
    return cost_report

# Alert for high costs
cost_alert = PythonOperator(
    task_id='send_cost_alerts',
    python_callable=send_cost_alerts,
    dag=dag
)

def send_cost_alerts(**context):
    """Send alerts if costs exceed thresholds"""
    execution_date = context['ds']
    
    # Check if alerts should be sent based on budget status
    # In reality would check actual cost data and send real alerts
    
    alerts_sent = {
        'date': execution_date,
        'alerts': [],
        'notifications_sent': 0
    }
    
    # Mock alert logic
    current_cost_percentage = 85.9  # From budget check
    
    if current_cost_percentage > 90:
        alerts_sent['alerts'].append('CRITICAL: Daily budget 90% exceeded')
        alerts_sent['notifications_sent'] += 1
    elif current_cost_percentage > 80:
        alerts_sent['alerts'].append('WARNING: Daily budget 80% exceeded')
        alerts_sent['notifications_sent'] += 1
    
    print(f"Cost Alerts: {alerts_sent}")
    return alerts_sent

# Task dependencies
cost_group >> optimization_group >> cost_report >> cost_alert

# Documentation
dag.doc_md = """
### Cost Optimization Pipeline

Automated cost monitoring and optimization for AI model usage in the medallion architecture.

#### Key Features:
- **Real-time Cost Tracking**: Monitor costs across all AI models
- **Budget Alerts**: Automated notifications when approaching budget limits
- **Optimization Recommendations**: Data-driven suggestions for cost reduction
- **Model Efficiency Analysis**: Evaluate cost vs quality trade-offs
- **Batch Optimization**: Optimize batch sizes for maximum efficiency

#### Cost Management:
- Daily budget monitoring with 80% alert threshold
- Weekly and monthly budget tracking
- Cost trend analysis and predictions
- ROI analysis for model usage

#### Optimization Strategies:
1. **Embedding Optimization**: Use free models where quality permits
2. **Batch Size Tuning**: Optimize for API cost efficiency  
3. **Model Selection**: Choose most cost-effective models per task
4. **Quality Thresholds**: Balance quality requirements with costs

#### Alerting:
- Budget threshold alerts (80%, 90%, 100%)
- Cost spike detection (>20% daily increase)
- Model availability issues
- Optimization opportunity notifications

This pipeline helps maintain high-quality results while minimizing AI model costs.
"""