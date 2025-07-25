name: "Kafka Streaming Infrastructure - Real-time Ghost Story Collection PRP"
description: |

## Goal
Build a robust, production-ready Kafka streaming system that monitors PTT Marvel and Reddit for new ghost stories, triggers real-time data collection scripts, ensures reliable data flow to the medallion architecture with exactly-once semantics, and provides comprehensive monitoring and error handling. The system must achieve <30 seconds message processing latency, >99.9% stream uptime, and handle 10,000+ messages per hour during peak periods.

## Why
- **Business Value**: Enables real-time content discovery and reduces time-to-availability for new ghost stories from hours to minutes
- **User Impact**: Users can discover new ghost stories within 5 minutes of original posting on PTT or Reddit
- **Integration**: Seamlessly connects existing scrapers with medallion architecture through event-driven triggers
- **Problems Solved**:
  - Manual batch processing creates hours of delay for new content discovery
  - No automated coordination between PTT and Reddit collection systems
  - Missing real-time data pipeline for immediate bronze layer ingestion
  - Lack of stream health monitoring and automatic error recovery

## What
A complete Kafka streaming infrastructure with:
- **Local Kafka Cluster**: Self-hosted cluster with KRaft mode (no Zookeeper) for development and production
- **Real-time Monitoring**: Continuous monitoring producers for PTT Marvel and Reddit new post detection
- **Event-driven Processing**: Automatic execution of existing scraper scripts when new posts are detected
- **Stream Processing**: Kafka Streams for real-time data enrichment and validation before bronze layer storage
- **Comprehensive Monitoring**: Health metrics, throughput monitoring, and automatic error recovery
- **Security**: SSL/SASL authentication with proper access control and message encryption

### Success Criteria
- [ ] Message processing latency < 30 seconds from source detection to bronze layer storage
- [ ] Stream uptime > 99.9% availability with automatic failover and recovery mechanisms
- [ ] Throughput capacity: Handle 10,000+ messages per hour during peak periods
- [ ] Error recovery: >95% of transient failures recover automatically without manual intervention
- [ ] Data consistency: Zero message loss with exactly-once processing semantics guaranteed
- [ ] Resource efficiency: <$150/month in infrastructure costs with optimized resource allocation
- [ ] All validation gates pass without manual intervention

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://kafka.apache.org/documentation/
  why: Official Kafka documentation for core concepts and configuration
  
- url: https://docs.confluent.io/kafka-clients/python/current/overview.html
  why: Confluent Kafka Python client documentation and best practices
  
- url: https://kafka.apache.org/documentation/streams/
  why: Kafka Streams API for real-time stream processing and data enrichment

- url: https://docs.docker.com/compose/
  why: Docker Compose for local Kafka cluster deployment and orchestration

- file: examples/etl/web-scraper/scrapers/ptt_scraper_pure.py
  why: Existing PTT scraper pattern with error handling and database integration
  
- file: examples/etl/web-scraper/scrapers/reddit_scraper.py
  why: Advanced Reddit scraper with rate limiting, retry logic, and failed job tracking
  
- file: examples/etl/web-scraper/scripts/REDDIT_RATE_LIMITING_GUIDE.md
  why: Sophisticated rate limiting strategies and error handling patterns
  
- file: examples/infrastructure/database/connection.py
  why: Database connection patterns with context managers and error handling
  
- file: examples/etl/processing/config.py
  why: Configuration pattern using dataclasses and environment variables
  
- file: examples/infrastructure/database/models.py
  why: Complete medallion architecture models for bronze layer integration

- docfile: PRPs/INITIAL_kafka_streaming.md
  why: Complete feature specification with detailed technical requirements and configurations
```

### Current Codebase tree
```bash
examples/
├── etl/
│   ├── processing/
│   │   ├── config.py              # Configuration patterns with dataclasses
│   │   ├── database.py            # Database manager with async operations
│   │   └── pipeline.py            # ETL pipeline orchestration patterns
│   └── web-scraper/
│       ├── scrapers/
│       │   ├── ptt_scraper_pure.py    # PTT scraper with database integration
│       │   └── reddit_scraper.py      # Advanced Reddit scraper with rate limiting
│       └── scripts/
│           ├── REDDIT_RATE_LIMITING_GUIDE.md  # Rate limiting strategies
│           └── streaming/
│               ├── PTT_stream_update.py       # Empty - needs implementation
│               └── Reddit_stream_update.py    # Empty - needs implementation
├── infrastructure/
│   ├── database/
│   │   ├── connection.py          # Database connection patterns
│   │   └── models.py              # Complete medallion architecture models
│   ├── kafka/
│   │   ├── producers.py           # Empty - needs implementation
│   │   ├── consumers.py           # Empty - needs implementation
│   │   └── topics.yaml            # Empty - needs configuration
│   └── airflow/
│       └── dags/
│           └── scraper.py         # Basic DAG pattern for integration
└── monitoring/
    └── alter/
        └── send_email.py          # Empty - needs alerting implementation
```

### Desired Codebase tree with files to be added
```bash
examples/
├── infrastructure/
│   ├── kafka/
│   │   ├── __init__.py
│   │   ├── config.py              # Kafka configuration with dataclass pattern
│   │   ├── producers.py           # PTT and Reddit monitoring producers
│   │   ├── consumers.py           # Scraping command and bronze ingestion consumers
│   │   ├── topics.yaml            # Topic configurations and retention policies
│   │   ├── streams.py             # Kafka Streams for real-time processing
│   │   ├── health_monitor.py      # Stream health monitoring and metrics
│   │   └── schema_registry.py     # Message schema management
│   ├── docker/
│   │   ├── docker-compose.kafka.yml    # Kafka cluster deployment
│   │   ├── kafka.env                   # Environment configuration
│   │   └── connectors/
│   │       └── postgresql-sink.json    # Kafka Connect configuration
│   └── monitoring/
│       ├── kafka_metrics.py       # Prometheus metrics collection
│       ├── alerts.py              # Alert management system
│       └── dashboards/
│           └── kafka_dashboard.py # Grafana dashboard configuration
├── etl/
│   └── streaming/
│       ├── __init__.py
│       ├── ptt_monitor.py         # PTT monitoring producer implementation
│       ├── reddit_monitor.py      # Reddit monitoring producer implementation
│       ├── scraper_dispatcher.py  # Event-driven scraper execution
│       └── stream_processor.py    # Data enrichment and validation
└── tests/
    ├── test_kafka/
    │   ├── test_producers.py
    │   ├── test_consumers.py
    │   └── test_streams.py
    └── integration/
        └── test_streaming_pipeline.py
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Poetry virtual environment must be activated
# poetry shell  # Required for all operations

# CRITICAL: Confluent Kafka Python requires librdkafka system library
# pip install confluent-kafka  # May need system dependencies
# On macOS: brew install librdkafka
# On Ubuntu: apt-get install librdkafka-dev

# CRITICAL: Kafka exactly-once semantics requires proper configuration
# producer_config = {
#     'enable.idempotence': True,
#     'acks': 'all', 
#     'max.in.flight.requests.per.connection': 5
# }

# CRITICAL: Message serialization must be consistent
# Use JSON with UTF-8 encoding for all messages
# Handle Chinese characters properly: json.dumps(data, ensure_ascii=False)

# CRITICAL: Consumer group coordination requires proper handling
# Always call consumer.close() in finally blocks
# Use consumer.commit() for manual offset management

# CRITICAL: Rate limiting integration with existing scrapers
# Follow existing patterns from reddit_scraper.py for backoff strategies
# Implement circuit breaker pattern for scraper failures

# GOTCHA: Kafka Connect requires specific format for PostgreSQL sink
# Message must have 'schema' and 'payload' fields for connector
# Use Avro or JSON Schema for proper data types

# GOTCHA: Docker Compose networking requires proper service names
# Use service names (kafka-1, kafka-2) not localhost in container communication
# Expose proper ports for external access: KAFKA_ADVERTISED_LISTENERS

# GOTCHA: KRaft mode (no Zookeeper) requires specific configuration
# KAFKA_PROCESS_ROLES: broker,controller
# KAFKA_CONTROLLER_QUORUM_VOTERS: Must list all controller nodes

# CRITICAL: Database integration must follow existing connection patterns
# Use examples/infrastructure/database/connection.py DatabaseManager
# Always use context managers: with db_manager.get_session() as session

# CRITICAL: Configuration must follow existing patterns
# Extend examples/etl/processing/config.py with KafkaConfig dataclass
# Use environment variables with sensible defaults
```

## Implementation Blueprint

### Configuration and Infrastructure Setup

Extend existing configuration patterns with Kafka-specific settings:

```python
# Task 1: Extend configuration
@dataclass
class KafkaConfig:
    """Kafka configuration following existing patterns"""
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    client_id: str = os.getenv("KAFKA_CLIENT_ID", "ghost-story-client")
    security_protocol: str = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    
    # Producer settings
    producer_acks: str = "all"
    producer_retries: int = 10
    producer_enable_idempotence: bool = True
    
    # Consumer settings  
    consumer_group_id: str = "ghost-story-consumers"
    consumer_auto_offset_reset: str = "latest"
    consumer_enable_auto_commit: bool = False
    
    # Topic settings
    default_replication_factor: int = 3
    default_partitions: int = 6
    retention_ms: int = 604800000  # 7 days
```

### List of tasks to be completed to fulfill the PRP in the order they should be completed

```yaml
Task 1: Foundation - Kafka Configuration and Docker Setup
CREATE examples/infrastructure/kafka/config.py:
  - MIRROR pattern from: examples/etl/processing/config.py
  - ADD KafkaConfig dataclass with environment variable defaults
  - INCLUDE producer, consumer, and topic configurations
  - ADD validation methods for configuration consistency

CREATE examples/infrastructure/docker/docker-compose.kafka.yml:
  - IMPLEMENT 3-broker Kafka cluster with KRaft mode
  - ADD Schema Registry and Kafka Connect services
  - INCLUDE proper networking and volume configurations
  - ADD environment variable configuration file

Task 2: Core Infrastructure - Producers and Topics
CREATE examples/infrastructure/kafka/topics.yaml:
  - DEFINE topic configurations with retention policies
  - INCLUDE partitioning strategy and replication factors
  - ADD compression and cleanup policies per topic type

CREATE examples/infrastructure/kafka/producers.py:
  - MIRROR pattern from: examples/etl/web-scraper/scrapers/reddit_scraper.py
  - IMPLEMENT PTTMonitoringProducer with error handling
  - IMPLEMENT RedditMonitoringProducer with rate limiting
  - ADD message serialization and delivery callbacks
  - INCLUDE health checking and metrics collection

Task 3: Consumer Implementation and Message Processing
CREATE examples/infrastructure/kafka/consumers.py:
  - MIRROR pattern from: examples/infrastructure/database/connection.py
  - IMPLEMENT ScrapingCommandConsumer for script triggering
  - IMPLEMENT BronzeIngestionConsumer for database storage
  - ADD proper offset management and error handling
  - INCLUDE dead letter queue processing

Task 4: Stream Processing and Data Enrichment
CREATE examples/infrastructure/kafka/streams.py:
  - IMPLEMENT Kafka Streams topology for data enrichment
  - ADD quality scoring and content validation filters
  - INCLUDE deduplication and format standardization
  - ADD cross-stream joins for correlation analysis

Task 5: Monitoring and Health Management
CREATE examples/infrastructure/kafka/health_monitor.py:
  - MIRROR pattern from: examples/etl/web-scraper/scrapers/reddit_scraper.py (failed jobs tracking)
  - IMPLEMENT StreamHealthMonitor for metrics collection
  - ADD consumer lag monitoring and alerting
  - INCLUDE automatic scaling triggers and health checks

CREATE examples/infrastructure/monitoring/kafka_metrics.py:
  - IMPLEMENT Prometheus metrics exposition
  - ADD custom metrics for business KPIs
  - INCLUDE JMX metrics integration for Kafka cluster
  - ADD grafana dashboard configuration

Task 6: Event-Driven Scraper Integration
CREATE examples/etl/streaming/ptt_monitor.py:
  - MIRROR pattern from: examples/etl/web-scraper/scrapers/ptt_scraper_pure.py
  - IMPLEMENT real-time PTT Marvel board monitoring
  - ADD new post detection and message publishing
  - INCLUDE error handling and rate limiting

CREATE examples/etl/streaming/reddit_monitor.py:
  - MIRROR pattern from: examples/etl/web-scraper/scrapers/reddit_scraper.py
  - IMPLEMENT real-time Reddit subreddit monitoring
  - ADD PRAW streaming API integration
  - INCLUDE rate limiting and API error handling

CREATE examples/etl/streaming/scraper_dispatcher.py:
  - IMPLEMENT event-driven script execution
  - ADD subprocess management for existing scrapers
  - INCLUDE result collection and error handling
  - ADD integration with bronze layer ingestion

Task 7: Security and Schema Management
CREATE examples/infrastructure/kafka/schema_registry.py:
  - IMPLEMENT message schema management
  - ADD schema evolution and compatibility checking
  - INCLUDE Avro schema definitions for messages
  - ADD validation and serialization helpers

Task 8: Error Handling and Recovery
CREATE examples/infrastructure/kafka/error_handler.py:
  - MIRROR pattern from: examples/etl/web-scraper/scripts/REDDIT_RATE_LIMITING_GUIDE.md
  - IMPLEMENT DeadLetterQueueHandler for failed messages
  - ADD exponential backoff and retry strategies
  - INCLUDE circuit breaker patterns for external services
  - ADD failed job tracking and manual review workflows

Task 9: Integration Testing and Deployment
CREATE examples/infrastructure/docker/kafka.env:
  - DEFINE environment variables for all services
  - INCLUDE security configurations and credentials
  - ADD development and production environment separation

CREATE deployment scripts:
  - CREATE cluster initialization and topic creation scripts
  - ADD health check and validation procedures
  - INCLUDE backup and disaster recovery procedures

Task 10: Comprehensive Testing Suite
CREATE tests/test_kafka/:
  - CREATE unit tests for all producers and consumers
  - ADD integration tests for message flow
  - INCLUDE performance and load testing
  - CREATE chaos engineering tests for failure scenarios
```

### Per task pseudocode as needed added to each task

```python
# Task 2: Core Producers Implementation
class PTTMonitoringProducer:
    def __init__(self, kafka_config: KafkaConfig):
        # PATTERN: Follow existing scraper initialization pattern
        self.producer = Producer({
            'bootstrap.servers': kafka_config.bootstrap_servers,
            'client.id': kafka_config.client_id,
            'enable.idempotence': True,  # CRITICAL for exactly-once
            'acks': 'all',
            'retries': kafka_config.producer_retries
        })
        self.last_seen_posts = {}  # Track already processed posts
        
    async def monitor_ptt_board(self):
        """Monitor PTT Marvel with existing scraper patterns"""
        while True:
            try:
                # PATTERN: Use existing PTT scraper logic for detection
                new_posts = await self.check_ptt_new_posts()
                
                for post in new_posts:
                    if self.is_new_post(post):
                        message = {
                            'source': 'ptt',
                            'post_id': post['id'],
                            'url': post['url'],
                            'title': post['title'],
                            'detection_time': datetime.utcnow().isoformat()
                        }
                        
                        # CRITICAL: Proper message serialization for Chinese text
                        self.producer.produce(
                            'ptt-new-posts',
                            key=post['id'].encode('utf-8'),
                            value=json.dumps(message, ensure_ascii=False).encode('utf-8'),
                            callback=self.delivery_callback
                        )
                        
                        # PATTERN: Follow reddit_scraper rate limiting
                        await self.apply_rate_limiting()
                        
            except Exception as e:
                # PATTERN: Follow existing error handling from scrapers
                await self.handle_monitoring_error('ptt', e)

# Task 3: Consumer Implementation
class ScrapingCommandConsumer:
    def __init__(self, kafka_config: KafkaConfig, db_manager: DatabaseManager):
        # PATTERN: Follow database connection pattern
        self.consumer = Consumer({
            'bootstrap.servers': kafka_config.bootstrap_servers,
            'group.id': kafka_config.consumer_group_id,
            'auto.offset.reset': kafka_config.consumer_auto_offset_reset,
            'enable.auto.commit': False  # Manual commit for exactly-once
        })
        self.db_manager = db_manager  # Use existing database manager
        
    async def process_messages(self):
        """Process messages with existing error handling patterns"""
        self.consumer.subscribe(['ptt-new-posts', 'reddit-new-posts'])
        
        while True:
            try:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                    
                if msg.error():
                    # PATTERN: Follow existing error handling
                    await self.handle_consumer_error(msg.error())
                    continue
                
                # Process message
                data = json.loads(msg.value().decode('utf-8'))
                
                if msg.topic() == 'ptt-new-posts':
                    await self.trigger_ptt_scraper(data)
                elif msg.topic() == 'reddit-new-posts':
                    await self.trigger_reddit_scraper(data)
                
                # CRITICAL: Manual commit for exactly-once semantics
                self.consumer.commit(msg)
                
            except Exception as e:
                # PATTERN: Follow existing failed job tracking
                await self.handle_processing_error(msg, e)

# Task 6: Event-driven Integration
async def trigger_ptt_scraper(self, post_data):
    """Execute existing scraper with subprocess pattern"""
    # PATTERN: Use existing scraper scripts
    command = [
        'poetry', 'run', 'python', 
        'examples/etl/web-scraper/scrapers/ptt_scraper_pure.py',
        '--post-url', post_data['url'],
        '--target-count', '1'
    ]
    
    # PATTERN: Follow existing subprocess management
    result = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await result.communicate()
    
    if result.returncode == 0:
        # Send success message to bronze ingestion topic
        await self.send_to_bronze_layer(post_data, stdout.decode())
    else:
        # PATTERN: Follow existing error handling
        await self.send_error_message('ptt_scraper', stderr.decode(), post_data)
```

### Integration Points
```yaml
DATABASE:
  - integration: "Use existing DatabaseManager from examples/infrastructure/database/connection.py"
  - pattern: "Follow context manager pattern for session management"
  - models: "Integrate with existing BronzeStory model from models.py"
  
CONFIG:
  - extend: examples/etl/processing/config.py
  - pattern: "Add KafkaConfig dataclass following existing pattern"
  - environment: "Use environment variables with sensible defaults"
  
SCRAPERS:
  - integrate: "Use existing scrapers as subprocess execution"  
  - pattern: "Follow rate limiting from reddit_scraper.py"
  - error_handling: "Mirror failed job tracking patterns"

MONITORING:
  - extend: examples/monitoring/ directory structure
  - pattern: "Follow existing logging and alerting patterns"
  - metrics: "Integrate with existing monitoring infrastructure"

DOCKER:
  - create: examples/infrastructure/docker/ for container orchestration
  - pattern: "Follow existing infrastructure organization"
  - networking: "Ensure proper service discovery and port mapping"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
poetry shell  # CRITICAL: Virtual environment activation required

# Install Kafka dependencies
poetry add confluent-kafka kafka-python avro-python3

# Code quality checks
poetry run ruff check examples/infrastructure/kafka/ --fix
poetry run mypy examples/infrastructure/kafka/ --ignore-missing-imports
poetry run black examples/infrastructure/kafka/ --check

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# CREATE tests/test_kafka/test_producers.py
import pytest
import json
from unittest.mock import Mock, patch
from examples.infrastructure.kafka.producers import PTTMonitoringProducer, RedditMonitoringProducer
from examples.infrastructure.kafka.config import KafkaConfig

@pytest.mark.asyncio
async def test_ptt_monitoring_producer_message_format():
    """Test PTT producer generates properly formatted messages"""
    config = KafkaConfig()
    producer = PTTMonitoringProducer(config)
    
    # Mock PTT post data
    post_data = {
        'id': 'test_123',
        'url': 'https://www.ptt.cc/bbs/marvel/M.1234567890.A.123.html',
        'title': '測試故事標題',
        'author': 'testuser'
    }
    
    with patch.object(producer, 'producer') as mock_producer:
        await producer.publish_new_post(post_data)
        
        # Verify message format
        mock_producer.produce.assert_called_once()
        call_args = mock_producer.produce.call_args
        
        assert call_args[1]['topic'] == 'ptt-new-posts'
        assert call_args[1]['key'] == b'test_123'
        
        # Parse and validate message content
        message = json.loads(call_args[1]['value'].decode('utf-8'))
        assert message['source'] == 'ptt'
        assert message['post_id'] == 'test_123'
        assert message['title'] == '測試故事標題'
        assert 'detection_time' in message

@pytest.mark.asyncio
async def test_consumer_exactly_once_semantics():
    """Test consumer implements exactly-once processing"""
    from examples.infrastructure.kafka.consumers import ScrapingCommandConsumer
    
    config = KafkaConfig()
    db_manager = Mock()
    consumer = ScrapingCommandConsumer(config, db_manager)
    
    # Mock Kafka message
    mock_msg = Mock()
    mock_msg.value.return_value = json.dumps({
        'source': 'ptt',
        'post_id': 'test_123',
        'url': 'https://test.url'
    }).encode('utf-8')
    mock_msg.topic.return_value = 'ptt-new-posts'
    mock_msg.error.return_value = None
    
    with patch.object(consumer, 'consumer') as mock_consumer:
        with patch.object(consumer, 'trigger_ptt_scraper') as mock_trigger:
            mock_consumer.poll.return_value = mock_msg
            mock_trigger.return_value = True
            
            await consumer.process_single_message()
            
            # Verify exactly-once: commit only after successful processing
            mock_trigger.assert_called_once()
            mock_consumer.commit.assert_called_once_with(mock_msg)

@pytest.mark.asyncio 
async def test_error_handling_and_retry():
    """Test error handling follows existing patterns"""
    from examples.infrastructure.kafka.error_handler import DeadLetterQueueHandler
    
    handler = DeadLetterQueueHandler(KafkaConfig())
    
    # Test exponential backoff calculation
    error_data = {
        'error_type': 'rate_limit_exceeded',
        'retry_count': 3,
        'original_message': {'test': 'data'}
    }
    
    should_retry = handler.should_retry(error_data)
    assert should_retry == True
    
    backoff_time = handler.calculate_backoff(error_data['retry_count'])
    assert backoff_time == 8  # 2^3 seconds exponential backoff
```

```bash
# Run and iterate until passing:
poetry run pytest tests/test_kafka/ -v --asyncio-mode=auto

# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test - Docker Compose Kafka Cluster
```bash
# Start Kafka cluster
docker-compose -f examples/infrastructure/docker/docker-compose.kafka.yml up -d

# Wait for cluster to be ready
sleep 30

# Create topics
poetry run python -c "
from examples.infrastructure.kafka.topics import create_topics
create_topics()
print('Topics created successfully')
"

# Test producer-consumer flow
poetry run python -c "
import asyncio
from examples.infrastructure.kafka.producers import PTTMonitoringProducer
from examples.infrastructure.kafka.consumers import ScrapingCommandConsumer
from examples.infrastructure.kafka.config import KafkaConfig

async def test_flow():
    config = KafkaConfig()
    producer = PTTMonitoringProducer(config)
    
    # Send test message
    test_post = {
        'id': 'integration_test_123',
        'url': 'https://test.url',
        'title': 'Integration Test Story'
    }
    
    await producer.publish_new_post(test_post)
    print('Test message sent successfully')

asyncio.run(test_flow())
"

# Expected: Messages flow through topics without errors
# Check logs: docker-compose logs kafka-1
```

### Level 4: End-to-End Streaming Pipeline Test
```bash
# Start all services
docker-compose -f examples/infrastructure/docker/docker-compose.kafka.yml up -d
poetry run python examples/etl/streaming/ptt_monitor.py &
poetry run python examples/etl/streaming/scraper_dispatcher.py &

# Simulate new post detection and verify bronze layer storage
poetry run python -c "
import asyncio
import json
from examples.infrastructure.kafka.config import KafkaConfig
from examples.infrastructure.kafka.producers import PTTMonitoringProducer
from examples.infrastructure.database.connection import db_manager

async def end_to_end_test():
    # Send test message to trigger pipeline
    producer = PTTMonitoringProducer(KafkaConfig())
    await producer.publish_new_post({
        'id': 'e2e_test_456',
        'url': 'https://www.ptt.cc/bbs/marvel/M.1234567890.A.456.html',
        'title': 'End-to-End Test Story'
    })
    
    # Wait for processing
    await asyncio.sleep(30)
    
    # Verify bronze layer storage
    with db_manager.get_session() as session:
        from examples.infrastructure.database.models import BronzeStory
        story = session.query(BronzeStory).filter(
            BronzeStory.source_url.contains('A.456.html')
        ).first()
        
        assert story is not None, 'Story not found in bronze layer'
        assert story.source == 'ptt_marvel'
        print('✅ End-to-end test passed: Story stored in bronze layer')

asyncio.run(end_to_end_test())
"

# Expected: Complete pipeline processes message and stores in database
```

## Final validation Checklist
- [ ] All tests pass: `poetry run pytest tests/ -v --asyncio-mode=auto`
- [ ] No linting errors: `poetry run ruff check examples/infrastructure/kafka/`
- [ ] No type errors: `poetry run mypy examples/infrastructure/kafka/ --ignore-missing-imports`
- [ ] Docker cluster starts successfully: `docker-compose up kafka-1 kafka-2 kafka-3`
- [ ] Topics create without errors: `kafka-topics --list --bootstrap-server localhost:9092`
- [ ] Producer-consumer message flow works: End-to-end test passes
- [ ] Database integration functions: Messages stored in bronze layer
- [ ] Error handling works: Failed messages go to dead letter queue
- [ ] Rate limiting respected: No rate limit violations in logs
- [ ] Monitoring metrics available: Prometheus metrics endpoint responding
- [ ] Security configured: SSL/SASL authentication works if enabled

---

## Anti-Patterns to Avoid
- ❌ Don't ignore exactly-once semantics - data integrity is critical
- ❌ Don't bypass existing rate limiting patterns - follow reddit_scraper.py approach
- ❌ Don't create new database connection patterns - use existing DatabaseManager
- ❌ Don't skip message serialization for Chinese characters - use ensure_ascii=False
- ❌ Don't use auto-commit consumers - manual commit required for exactly-once
- ❌ Don't ignore existing error handling patterns - mirror scraper failed job tracking
- ❌ Don't hardcode broker addresses - use environment variables like existing config
- ❌ Don't skip Docker networking configuration - service discovery requires proper setup
- ❌ Don't ignore existing logging patterns - integrate with current monitoring setup
- ❌ Don't create synchronous blocking operations - all Kafka operations should be async-compatible

---

## Confidence Score: 9/10

This PRP provides comprehensive context for one-pass implementation including:
✅ Complete analysis of existing codebase patterns (scrapers, database, config)
✅ Integration with existing infrastructure and error handling approaches
✅ Detailed technical specifications from comprehensive feature document
✅ Step-by-step implementation tasks with proper dependency ordering
✅ Executable validation gates with specific commands and expected outcomes
✅ Docker-based deployment approach following modern practices
✅ Exactly-once semantics and proper Kafka configuration
✅ Integration points clearly defined with existing database and monitoring systems
✅ Security considerations and production-ready configurations
✅ Performance requirements with measurable success criteria

The implementation should succeed in one pass given the detailed context, existing infrastructure patterns, and comprehensive validation framework provided.