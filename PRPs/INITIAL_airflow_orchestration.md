INITIAL_airflow_orchestration.md

## FEATURE: Apache Airflow ETL Pipeline Orchestration with Monitoring

Implement a comprehensive Apache Airflow system that orchestrates all ETL processes, manages medallion architecture workflows, provides real-time monitoring, and handles email notifications for our ghost story search engine platform.

## PRIMARY FUNCTIONALITY:
- **ETL Pipeline Orchestration:** Coordinate Bronze → Silver → Gold data transformations with proper dependency management
- **Multi-DAG Management:** Separate DAGs for PTT processing, Reddit processing, and cross-platform analytics
- **Real-time Monitoring:** Track pipeline health, performance metrics, and data quality in real-time
- **Email Notifications:** Automated alerts to Gmail for failures, completions, and data quality issues
- **Error Handling:** Comprehensive retry mechanisms, failure recovery, and dead letter handling
- **Resource Management:** Optimize worker allocation and task scheduling for cost efficiency
- **Data Quality Integration:** Built-in data validation and quality checks at each pipeline stage

## ADDITIONAL FEATURES:
- **Dynamic DAG Generation:** Template-based DAG creation for easy scaling to new data sources
- **Cross-DAG Dependencies:** Coordinate dependencies between PTT, Reddit, and analytics pipelines
- **SLA Monitoring:** Track and alert on pipeline completion times and performance degradation
- **Custom Operators:** Specialized operators for ghost story processing, embedding generation, and quality scoring
- **Variable Management:** Centralized configuration management with environment-specific settings
- **Audit Logging:** Comprehensive logging of all pipeline executions and data transformations
- **Cost Optimization:** Intelligent scheduling to minimize cloud resource costs during off-peak hours

## TECHNICAL REQUIREMENTS:
- **Apache Airflow 2.5+** with LocalExecutor for development and CeleryExecutor for production
- **PostgreSQL backend** for Airflow metadata storage with proper indexing and performance optimization
- **Redis message broker** for Celery worker coordination and task distribution
- **Docker containerization** with Poetry dependency management and multi-stage builds
- **Custom operators** for PTT scraping, Reddit API calls, DeepSeek/LLaMA processing, and embedding generation
- **Great Expectations integration** for automated data quality validation and reporting
- **Prometheus metrics** export for monitoring integration with Grafana dashboards
- **SMTP integration** for Gmail notifications with proper authentication and security

## DAG ARCHITECTURE:

### PTT_ETL_DAG (Traditional Chinese Processing):
```python
# DAG Structure:
# Bronze Ingestion → Data Validation → Silver Processing → Quality Check → Gold Aggregation

Task Dependencies:
1. monitor_ptt_new_posts → trigger_ptt_scraper
2. ptt_bronze_ingestion → validate_bronze_data
3. validate_bronze_data → ptt_silver_processing
4. ptt_silver_processing → deepseek_chunking
5. deepseek_chunking → chinese_embedding_generation
6. chinese_embedding_generation → quality_scoring
7. quality_scoring → ptt_gold_aggregation
8. ptt_gold_aggregation → send_completion_email
```

**Task Specifications:**
- **Schedule:** Daily at 2:00 AM UTC with catchup enabled
- **Retries:** 3 attempts with exponential backoff (1, 2, 4 minutes)
- **SLA:** 4 hours for complete pipeline execution
- **Email on failure:** Immediate notification with error details and suggested remediation
- **Resource allocation:** 2GB memory, 1 CPU core per task

### Reddit_ETL_DAG (English Processing):
```python
# DAG Structure:
# API Polling → Bronze Storage → Validation → Silver Transform → Gold Analytics

Task Dependencies:
1. reddit_api_polling → reddit_bronze_ingestion
2. reddit_bronze_ingestion → validate_reddit_data
3. validate_reddit_data → reddit_silver_processing
4. reddit_silver_processing → llama_chunking
5. llama_chunking → english_embedding_generation
6. english_embedding_generation → content_classification
7. content_classification → reddit_gold_aggregation
8. reddit_gold_aggregation → update_search_index
```

**Task Specifications:**
- **Schedule:** Every 6 hours with offset to avoid PTT pipeline conflicts
- **Retries:** 5 attempts for API-dependent tasks, 3 for processing tasks
- **SLA:** 2 hours for complete pipeline execution
- **Rate limiting:** Built-in Reddit API compliance with backoff strategies
- **Resource allocation:** 4GB memory for LLaMA processing, 2GB for other tasks

### Cross_Platform_Analytics_DAG (Business Intelligence):
```python
# DAG Structure:
# Wait for PTT & Reddit → Cross-platform Analysis → User Analytics → Business Metrics

Task Dependencies:
1. wait_for_ptt_completion & wait_for_reddit_completion → cross_platform_analysis
2. cross_platform_analysis → user_behavior_analytics
3. user_behavior_analytics → freemium_conversion_analysis
4. freemium_conversion_analysis → business_metrics_calculation
5. business_metrics_calculation → analytics_dashboard_update
6. analytics_dashboard_update → daily_business_report
```

**Task Specifications:**
- **Schedule:** Daily at 8:00 AM UTC (after PTT and Reddit pipelines complete)
- **Dependencies:** External sensor tasks waiting for upstream DAG completion
- **SLA:** 1 hour for analytics processing
- **Business focus:** Revenue analytics, user engagement, content performance

## CUSTOM AIRFLOW OPERATORS:

### PTTScrapingOperator:
```python
class PTTScrapingOperator(BaseOperator):
    """Custom operator for PTT Marvel scraping with Traditional Chinese handling"""
    
    def __init__(self, board_name, date_range, rate_limit, **kwargs):
        super().__init__(**kwargs)
        self.board_name = board_name
        self.date_range = date_range
        self.rate_limit = rate_limit
    
    def execute(self, context):
        # Implementation with proper error handling and progress tracking
        pass
```

### EmbeddingGenerationOperator:
```python
class EmbeddingGenerationOperator(BaseOperator):
    """Operator for generating embeddings with cost optimization"""
    
    def __init__(self, model_type, batch_size, cost_threshold, **kwargs):
        super().__init__(**kwargs)
        self.model_type = model_type  # 'openai', 'sentence-transformers'
        self.batch_size = batch_size
        self.cost_threshold = cost_threshold
```

### DataQualityOperator:
```python
class DataQualityOperator(BaseOperator):
    """Great Expectations integration for data validation"""
    
    def __init__(self, expectation_suite, checkpoint_name, **kwargs):
        super().__init__(**kwargs)
        self.expectation_suite = expectation_suite
        self.checkpoint_name = checkpoint_name
```

## MONITORING & ALERTING CONFIGURATION:

### Email Notification System:
```python
# Airflow email configuration
EMAIL_CONFIG = {
    'smtp_host': 'smtp.gmail.com',
    'smtp_starttls': True,
    'smtp_ssl': False,
    'smtp_port': 587,
    'smtp_mail_from': 'ghoststory.alerts@gmail.com'
}

# Notification templates
FAILURE_EMAIL_TEMPLATE = """
Pipeline Failure Alert - Ghost Story ETL

DAG: {{ dag.dag_id }}
Task: {{ task.task_id }}
Execution Date: {{ ds }}
Log URL: {{ task_instance.log_url }}

Error Details:
{{ exception }}

Suggested Actions:
{{ remediation_steps }}
"""

SUCCESS_EMAIL_TEMPLATE = """
Pipeline Completion - Ghost Story ETL

DAG: {{ dag.dag_id }}
Execution Date: {{ ds }}
Duration: {{ dag_run.duration }}

Metrics:
- Stories Processed: {{ ti.xcom_pull(key='stories_processed') }}
- Quality Score: {{ ti.xcom_pull(key='avg_quality_score') }}
- Embeddings Generated: {{ ti.xcom_pull(key='embeddings_count') }}

Dashboard: https://ghoststory-analytics.com/dashboard
"""
```

### SLA Monitoring:
```python
# SLA configuration for each DAG
PTT_SLA_CONFIG = {
    'sla': timedelta(hours=4),
    'sla_miss_callback': send_sla_miss_email,
    'email_on_failure': True,
    'email_on_retry': False,
    'email_on_success': True
}

def send_sla_miss_email(dag, task_list, blocking_task_list, slas, blocking_tis):
    """Custom SLA miss notification with detailed context"""
    # Implementation for SLA violation handling
    pass
```

## ERROR HANDLING & RECOVERY:

### Retry Strategy:
```python
# Task-specific retry configuration
RETRY_CONFIG = {
    'scraping_tasks': {
        'retries': 5,
        'retry_delay': timedelta(minutes=1),
        'retry_exponential_backoff': True,
        'max_retry_delay': timedelta(minutes=10)
    },
    'processing_tasks': {
        'retries': 3,
        'retry_delay': timedelta(minutes=2),
        'retry_exponential_backoff': True
    },
    'api_tasks': {
        'retries': 10,
        'retry_delay': timedelta(seconds=30),
        'retry_exponential_backoff': True
    }
}
```

### Dead Letter Queue Handling:
```python
def handle_failed_task(context):
    """Handle permanently failed tasks with dead letter processing"""
    task_instance = context['task_instance']
    
    # Log to dead letter queue
    dead_letter_entry = {
        'dag_id': task_instance.dag_id,
        'task_id': task_instance.task_id,
        'execution_date': context['ds'],
        'error_message': str(context.get('exception')),
        'retry_count': task_instance.try_number,
        'created_at': datetime.utcnow()
    }
    
    # Store in database for manual review
    store_dead_letter_entry(dead_letter_entry)
    
    # Notify engineering team
    send_dead_letter_alert(dead_letter_entry)
```

## PERFORMANCE OPTIMIZATION:

### Resource Management:
```python
# Pool configuration for resource allocation
AIRFLOW_POOLS = {
    'ptt_processing_pool': {
        'slots': 4,
        'description': 'PTT processing tasks with Traditional Chinese handling'
    },
    'reddit_api_pool': {
        'slots': 2,
        'description': 'Reddit API calls with rate limiting'
    },
    'embedding_generation_pool': {
        'slots': 1,
        'description': 'Expensive embedding generation tasks'
    },
    'database_pool': {
        'slots': 8,
        'description': 'Database operations and queries'
    }
}
```

### Cost Optimization:
```python
# Intelligent scheduling for cost reduction
def get_optimal_schedule_time():
    """Calculate optimal execution time based on cloud pricing"""
    # Schedule during off-peak hours for cost savings
    return '0 2 * * *'  # 2 AM UTC when AWS costs are lower

# Resource scaling based on workload
def calculate_worker_resources(estimated_stories):
    """Dynamic resource allocation based on expected workload"""
    if estimated_stories > 10000:
        return {'cpu': 4, 'memory': '8Gi'}
    elif estimated_stories > 5000:
        return {'cpu': 2, 'memory': '4Gi'}
    else:
        return {'cpu': 1, 'memory': '2Gi'}
```

## USER STORIES:
- As a **data engineer**, I can monitor all ETL pipelines from a single Airflow dashboard with real-time status updates
- As a **developer**, I receive immediate email notifications when pipelines fail with detailed error context and suggested fixes
- As a **business analyst**, I can track pipeline performance and data quality metrics to ensure reliable analytics
- As an **admin**, I can easily add new data sources by templating existing DAGs without manual configuration
- As a **product manager**, I receive daily email reports with business metrics and pipeline health summaries
- As a **data scientist**, I can depend on consistent, high-quality data delivery for machine learning model training

## SUCCESS CRITERIA:
- **Pipeline uptime:** >99.5% across all DAGs with minimal manual intervention
- **SLA compliance:** >95% of pipelines complete within defined time windows
- **Email delivery:** 100% notification delivery for critical events within 2 minutes
- **Error recovery:** >90% of transient failures recover automatically without manual intervention
- **Resource efficiency:** <$200/month in cloud compute costs with optimized scheduling
- **Data quality:** >95% pass rate for all Great Expectations validation checks
- **Monitoring coverage:** 100% of critical tasks monitored with appropriate alerting

## INTEGRATION POINTS:
- **Kafka streaming integration** for real-time task triggering and event coordination
- **PostgreSQL medallion architecture** for data storage and retrieval across all layers
- **Vector database integration** for embedding storage and similarity search updates
- **Prometheus metrics export** for comprehensive monitoring and alerting infrastructure
- **Great Expectations integration** for automated data quality validation and reporting
- **Slack/Gmail notifications** for team communication and incident response
- **Cost monitoring integration** with cloud provider APIs for budget tracking

## DEPLOYMENT & INFRASTRUCTURE:
- **Docker containerization** with Poetry dependency management and optimized builds
- **Kubernetes deployment** with auto-scaling worker pools and resource management
- **Infrastructure as Code** using Terraform for reproducible Airflow cluster setup
- **CI/CD pipeline** for DAG deployment with automated testing and validation
- **Environment separation** (dev/staging/prod) with proper configuration management
- **High availability** setup with Redis clustering and PostgreSQL replication

## SECURITY & COMPLIANCE:
- **Role-based access control** for DAG execution and monitoring with proper user permissions
- **Secrets management** using Kubernetes secrets or HashiCorp Vault for API keys
- **Audit logging** for all pipeline executions and configuration changes
- **Network security** with VPC isolation and encrypted communication channels
- **Data privacy compliance** with GDPR-compliant data handling and retention policies
- **Access monitoring** with logging and alerting for unauthorized access attempts

## OTHER CONSIDERATIONS:
- **Documentation standards** including DAG descriptions, task documentation, and troubleshooting guides
- **Team collaboration** tools for shared DAG development and debugging procedures
- **Capacity planning** for growth projection and resource scaling requirements
- **Disaster recovery** procedures with backup strategies and emergency runbooks
- **Performance tuning** guidelines for optimizing task execution and resource utilization
- **Future extensibility** for additional data sources and processing requirements
- **Training materials** for team onboarding and Airflow best practices