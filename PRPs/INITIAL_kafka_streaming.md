INITIAL_kafka_streaming.md

## FEATURE: Kafka Streaming Infrastructure for Real-time Ghost Story Collection

Build a robust, production-ready Kafka streaming system that monitors PTT Marvel and Reddit for new ghost stories, triggers real-time data collection scripts, ensures reliable data flow to the medallion architecture, and provides comprehensive monitoring and error handling.

## PRIMARY FUNCTIONALITY:
- **Local Kafka Cluster Setup:** Self-hosted Kafka cluster with Zookeeper coordination for development and production
- **Real-time Endpoint Monitoring:** Continuous monitoring of PTT Marvel and Reddit subreddits for new post detection
- **Event-driven Script Triggering:** Automatic execution of `PTT_marvel_realtime_data_collect.py` and `Reddit_realtime_data_collect.py` when new posts are detected
- **Bronze Layer Integration:** Direct streaming ingestion to bronze layer with exactly-once semantic guarantees
- **Comprehensive Error Logging:** Structured error logging with automatic retry mechanisms and dead letter queue handling
- **Stream Health Monitoring:** Real-time monitoring of stream health, throughput, and latency metrics

## ADDITIONAL FEATURES:
- **Kafka Connect Integration:** Direct database connectors for seamless bronze layer ingestion without custom code
- **Stream Processing Pipeline:** Real-time data enrichment and validation using Kafka Streams before database storage
- **Dynamic Scaling:** Automatic partition scaling and consumer group rebalancing based on message volume
- **Message Deduplication:** Built-in duplicate detection to prevent reprocessing of identical content
- **Security and Authentication:** SSL/SASL authentication with proper access control and message encryption
- **Retention Policy Management:** Configurable retention policies for different message types and compliance requirements
- **Cross-platform Coordination:** Intelligent coordination between PTT and Reddit streams to avoid resource conflicts

## TECHNICAL REQUIREMENTS:
- **Apache Kafka 3.5+** with KRaft mode (no Zookeeper dependency) for simplified deployment
- **Confluent Kafka Python Client** for high-performance producers and consumers with proper error handling
- **Kafka Connect** with PostgreSQL sink connectors for direct database integration
- **Kafka Streams** for real-time stream processing and data transformation
- **Docker Compose** for local development with Poetry dependency management
- **Prometheus metrics** export for monitoring integration with Grafana dashboards
- **Schema Registry** for message format evolution and backward compatibility
- **KSQL** for real-time stream analytics and monitoring queries

## KAFKA CLUSTER ARCHITECTURE:

### Broker Configuration:
```yaml
# kafka-cluster.yml
services:
  kafka-broker-1:
    image: confluentinc/cp-kafka:7.4.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-broker-1:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_LOG_RETENTION_HOURS: 168  # 7 days
      KAFKA_LOG_SEGMENT_BYTES: 1073741824  # 1GB
      KAFKA_NUM_PARTITIONS: 6
    volumes:
      - kafka-broker-1-data:/var/lib/kafka/data
    ports:
      - "9092:9092"
```

### Topic Configuration:
```python
KAFKA_TOPICS = {
    'ptt-new-posts': {
        'partitions': 6,
        'replication_factor': 3,
        'config': {
            'retention.ms': 604800000,  # 7 days
            'compression.type': 'snappy',
            'cleanup.policy': 'delete'
        }
    },
    'reddit-new-posts': {
        'partitions': 6,
        'replication_factor': 3,
        'config': {
            'retention.ms': 604800000,
            'compression.type': 'snappy',
            'cleanup.policy': 'delete'
        }
    },
    'scraping-commands': {
        'partitions': 3,
        'replication_factor': 3,
        'config': {
            'retention.ms': 86400000,  # 1 day
            'compression.type': 'gzip'
        }
    },
    'bronze-ingestion': {
        'partitions': 12,
        'replication_factor': 3,
        'config': {
            'retention.ms': 2592000000,  # 30 days
            'compression.type': 'lz4',
            'cleanup.policy': 'delete'
        }
    },
    'processing-errors': {
        'partitions': 3,
        'replication_factor': 3,
        'config': {
            'retention.ms': 2592000000,  # 30 days
            'compression.type': 'gzip',
            'cleanup.policy': 'compact'
        }
    },
    'system-alerts': {
        'partitions': 1,
        'replication_factor': 3,
        'config': {
            'retention.ms': 604800000,  # 7 days
            'compression.type': 'snappy'
        }
    }
}
```

## STREAMING PRODUCERS:

### PTT Monitoring Producer:
```python
class PTTMonitoringProducer:
    """Producer for monitoring PTT Marvel board and detecting new posts"""
    
    def __init__(self, kafka_config, ptt_config):
        self.producer = KafkaProducer(**kafka_config)
        self.ptt_config = ptt_config
        self.last_seen_posts = {}
        
    async def monitor_ptt_board(self):
        """Continuously monitor PTT Marvel for new posts"""
        while True:
            try:
                new_posts = await self.check_ptt_new_posts()
                for post in new_posts:
                    message = {
                        'source': 'ptt',
                        'board': 'marvel',
                        'post_id': post['id'],
                        'url': post['url'],
                        'title': post['title'],
                        'author': post['author'],
                        'timestamp': post['timestamp'],
                        'detection_time': datetime.utcnow().isoformat()
                    }
                    
                    self.producer.send(
                        'ptt-new-posts',
                        key=post['id'].encode('utf-8'),
                        value=json.dumps(message).encode('utf-8')
                    )
                    
                await asyncio.sleep(self.ptt_config['polling_interval'])
                
            except Exception as e:
                await self.handle_monitoring_error('ptt', e)
```

### Reddit Monitoring Producer:
```python
class RedditMonitoringProducer:
    """Producer for monitoring Reddit subreddits and detecting new posts"""
    
    def __init__(self, kafka_config, reddit_config):
        self.producer = KafkaProducer(**kafka_config)
        self.reddit = praw.Reddit(**reddit_config)
        self.monitored_subreddits = ['nosleep', 'paranormal', 'Glitch_in_the_Matrix']
        
    async def monitor_subreddits(self):
        """Monitor multiple subreddits for new ghost stories"""
        for subreddit_name in self.monitored_subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                for submission in subreddit.new(limit=10):
                    if self.is_new_post(submission) and self.is_ghost_story(submission):
                        message = {
                            'source': 'reddit',
                            'subreddit': subreddit_name,
                            'post_id': submission.id,
                            'url': submission.url,
                            'title': submission.title,
                            'author': str(submission.author),
                            'score': submission.score,
                            'created_utc': submission.created_utc,
                            'detection_time': datetime.utcnow().isoformat()
                        }
                        
                        self.producer.send(
                            'reddit-new-posts',
                            key=submission.id.encode('utf-8'),
                            value=json.dumps(message).encode('utf-8')
                        )
                        
            except Exception as e:
                await self.handle_monitoring_error('reddit', e)
```

## STREAMING CONSUMERS:

### Scraping Command Consumer:
```python
class ScrapingCommandConsumer:
    """Consumer that triggers scraping scripts based on new post detection"""
    
    def __init__(self, kafka_config):
        self.consumer = KafkaConsumer(
            'ptt-new-posts',
            'reddit-new-posts',
            **kafka_config,
            group_id='scraping-trigger-group',
            auto_offset_reset='latest',
            enable_auto_commit=True
        )
        
    async def process_messages(self):
        """Process incoming messages and trigger appropriate scrapers"""
        for message in self.consumer:
            try:
                data = json.loads(message.value.decode('utf-8'))
                
                if message.topic == 'ptt-new-posts':
                    await self.trigger_ptt_scraper(data)
                elif message.topic == 'reddit-new-posts':
                    await self.trigger_reddit_scraper(data)
                    
                # Acknowledge successful processing
                self.consumer.commit()
                
            except Exception as e:
                await self.handle_processing_error(message, e)
    
    async def trigger_ptt_scraper(self, post_data):
        """Execute PTT real-time scraper for specific post"""
        command = [
            'python', 'scrapers/PTT_marvel_realtime_data_collect.py',
            '--post-url', post_data['url'],
            '--post-id', post_data['post_id']
        ]
        
        result = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            # Send success message to bronze ingestion
            await self.send_to_bronze_layer(post_data, stdout.decode())
        else:
            # Send error to error topic
            await self.send_error_message('ptt_scraper', stderr.decode(), post_data)
```

### Bronze Layer Ingestion Consumer:
```python
class BronzeIngestionConsumer:
    """Consumer for direct bronze layer database ingestion"""
    
    def __init__(self, kafka_config, db_config):
        self.consumer = KafkaConsumer(
            'bronze-ingestion',
            **kafka_config,
            group_id='bronze-ingestion-group',
            auto_offset_reset='earliest'
        )
        self.db_engine = create_async_engine(db_config['url'])
        
    async def process_bronze_ingestion(self):
        """Process messages for bronze layer storage"""
        for message in self.consumer:
            try:
                data = json.loads(message.value.decode('utf-8'))
                
                async with self.db_engine.begin() as conn:
                    if data['source'] == 'ptt':
                        await self.insert_bronze_ptt_story(conn, data)
                    elif data['source'] == 'reddit':
                        await self.insert_bronze_reddit_story(conn, data)
                
                # Update processing metrics
                await self.update_processing_metrics(data)
                
            except Exception as e:
                await self.handle_ingestion_error(message, e)
```

## KAFKA STREAMS PROCESSING:

### Real-time Data Enrichment:
```python
from kafka import KafkaStreams, StreamsBuilder

def create_data_enrichment_topology():
    """Create Kafka Streams topology for real-time data enrichment"""
    
    builder = StreamsBuilder()
    
    # Source streams
    ptt_stream = builder.stream('ptt-new-posts')
    reddit_stream = builder.stream('reddit-new-posts')
    
    # Data enrichment processing
    enriched_ptt = (ptt_stream
                   .map_values(lambda value: enrich_ptt_data(value))
                   .filter(lambda key, value: value['quality_score'] > 0.7))
    
    enriched_reddit = (reddit_stream
                      .map_values(lambda value: enrich_reddit_data(value))
                      .filter(lambda key, value: value['quality_score'] > 0.7))
    
    # Merge streams and send to bronze ingestion
    merged_stream = enriched_ptt.merge(enriched_reddit)
    merged_stream.to('bronze-ingestion')
    
    return builder.build()

def enrich_ptt_data(raw_data):
    """Enrich PTT data with quality scoring and metadata"""
    enriched = raw_data.copy()
    enriched['quality_score'] = calculate_ptt_quality_score(raw_data)
    enriched['language'] = 'zh-TW'
    enriched['estimated_reading_time'] = estimate_reading_time_chinese(raw_data['title'])
    enriched['content_type'] = classify_ptt_content(raw_data)
    return enriched
```

## ERROR HANDLING & MONITORING:

### Dead Letter Queue Processing:
```python
class DeadLetterQueueHandler:
    """Handle failed messages and retry processing"""
    
    def __init__(self, kafka_config):
        self.consumer = KafkaConsumer(
            'processing-errors',
            **kafka_config,
            group_id='dlq-handler-group'
        )
        self.producer = KafkaProducer(**kafka_config)
        
    async def process_failed_messages(self):
        """Process failed messages with intelligent retry logic"""
        for message in self.consumer:
            try:
                error_data = json.loads(message.value.decode('utf-8'))
                
                # Analyze error and determine retry strategy
                if self.should_retry(error_data):
                    await self.retry_processing(error_data)
                else:
                    await self.send_to_manual_review(error_data)
                    
            except Exception as e:
                # Log critical error handling failure
                logger.critical(f"DLQ processing failed: {e}")
```

### Stream Health Monitoring:
```python
class StreamHealthMonitor:
    """Monitor stream health and performance metrics"""
    
    def __init__(self, kafka_config):
        self.admin_client = KafkaAdminClient(**kafka_config)
        self.metrics_producer = KafkaProducer(**kafka_config)
        
    async def collect_stream_metrics(self):
        """Collect and publish stream health metrics"""
        while True:
            try:
                metrics = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'topic_metrics': await self.get_topic_metrics(),
                    'consumer_lag': await self.get_consumer_lag(),
                    'producer_throughput': await self.get_producer_throughput(),
                    'error_rates': await self.get_error_rates()
                }
                
                self.metrics_producer.send(
                    'system-alerts',
                    value=json.dumps(metrics).encode('utf-8')
                )
                
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
                
            except Exception as e:
                logger.error(f"Metrics collection failed: {e}")
```

## USER STORIES:
- As a **data engineer**, I can monitor real-time data ingestion rates and stream health through comprehensive dashboards
- As a **developer**, I can add new data sources by simply configuring new topics without complex infrastructure changes
- As a **user**, I can discover new ghost stories within 5 minutes of their original posting on PTT or Reddit
- As an **admin**, I receive immediate alerts when stream processing fails or performance degrades
- As a **business analyst**, I can track content acquisition rates and source performance in real-time
- As a **system operator**, I can scale streaming capacity automatically based on message volume and processing demands

## SUCCESS CRITERIA:
- **Message processing latency:** <30 seconds from source detection to bronze layer storage
- **Stream uptime:** >99.9% availability with automatic failover and recovery mechanisms
- **Throughput capacity:** Handle 10,000+ messages per hour during peak periods without performance degradation
- **Error recovery:** >95% of transient failures recover automatically without manual intervention
- **Data consistency:** Zero message loss with exactly-once processing semantics guaranteed
- **Resource efficiency:** <$150/month in infrastructure costs with optimized resource allocation
- **Monitoring coverage:** 100% of critical streams monitored with sub-minute alert response times

## INTEGRATION POINTS:
- **Airflow DAG triggering** for coordinated batch processing when real-time streams reach thresholds
- **PostgreSQL medallion architecture** for seamless bronze layer ingestion with transactional consistency
- **Prometheus metrics export** for comprehensive monitoring integration with existing infrastructure
- **Email/Slack alerting** for immediate notification of stream failures and performance issues
- **Great Expectations integration** for real-time data quality validation before bronze layer insertion
- **Vector database updates** for immediate embedding index updates when new content is processed
- **Cost monitoring APIs** for tracking infrastructure expenses and optimizing resource allocation

## PERFORMANCE OPTIMIZATION:

### Message Compression and Serialization:
```python
# Optimized producer configuration
PRODUCER_CONFIG = {
    'bootstrap_servers': ['localhost:9092'],
    'compression_type': 'lz4',  # Best balance of speed and compression
    'batch_size': 16384,  # 16KB batches for efficiency
    'linger_ms': 10,  # Small delay for batching
    'acks': 'all',  # Ensure durability
    'retries': 10,
    'retry_backoff_ms': 100,
    'buffer_memory': 33554432,  # 32MB buffer
    'max_in_flight_requests_per_connection': 5
}

# Optimized consumer configuration
CONSUMER_CONFIG = {
    'bootstrap_servers': ['localhost:9092'],
    'auto_offset_reset': 'latest',
    'enable_auto_commit': False,  # Manual commit for exactly-once
    'fetch_min_bytes': 1024,  # Minimum fetch size
    'fetch_max_wait_ms': 500,  # Maximum wait time
    'max_partition_fetch_bytes': 1048576,  # 1MB max per partition
    'session_timeout_ms': 30000,
    'heartbeat_interval_ms': 3000
}
```

### Auto-scaling Configuration:
```python
class KafkaAutoScaler:
    """Automatic scaling based on message volume and processing lag"""
    
    def __init__(self, kafka_config, scaling_config):
        self.admin_client = KafkaAdminClient(**kafka_config)
        self.scaling_config = scaling_config
        
    async def monitor_and_scale(self):
        """Monitor consumer lag and scale partitions/consumers accordingly"""
        while True:
            lag_metrics = await self.get_consumer_lag_metrics()
            
            for topic, lag in lag_metrics.items():
                if lag > self.scaling_config['scale_up_threshold']:
                    await self.scale_up_topic(topic)
                elif lag < self.scaling_config['scale_down_threshold']:
                    await self.scale_down_topic(topic)
            
            await asyncio.sleep(60)  # Check every minute
    
    async def scale_up_topic(self, topic_name):
        """Increase partitions for high-lag topics"""
        current_partitions = await self.get_partition_count(topic_name)
        new_partitions = min(current_partitions * 2, self.scaling_config['max_partitions'])
        
        if new_partitions > current_partitions:
            await self.admin_client.create_partitions({
                topic_name: NewPartitions(total_count=new_partitions)
            })
            logger.info(f"Scaled up {topic_name} to {new_partitions} partitions")
```

## SECURITY CONFIGURATION:

### SSL/SASL Authentication:
```yaml
# kafka-security.yml
security:
  ssl:
    enabled: true
    keystore_location: /etc/kafka/ssl/kafka.server.keystore.jks
    keystore_password: ${KAFKA_KEYSTORE_PASSWORD}
    truststore_location: /etc/kafka/ssl/kafka.server.truststore.jks
    truststore_password: ${KAFKA_TRUSTSTORE_PASSWORD}
  
  sasl:
    enabled: true
    mechanism: SCRAM-SHA-512
    jaas_config: |
      org.apache.kafka.common.security.scram.ScramLoginModule required
      username="${KAFKA_USERNAME}"
      password="${KAFKA_PASSWORD}";
```

### Access Control Lists (ACLs):
```python
# ACL configuration for different user roles
KAFKA_ACLS = {
    'ghost-story-producers': {
        'operations': ['WRITE', 'DESCRIBE'],
        'topics': ['ptt-new-posts', 'reddit-new-posts', 'system-alerts']
    },
    'ghost-story-consumers': {
        'operations': ['READ', 'DESCRIBE'],
        'topics': ['ptt-new-posts', 'reddit-new-posts', 'bronze-ingestion']
    },
    'ghost-story-processors': {
        'operations': ['READ', 'WRITE', 'DESCRIBE'],
        'topics': ['bronze-ingestion', 'processing-errors', 'system-alerts']
    },
    'ghost-story-admins': {
        'operations': ['ALL'],
        'topics': ['*']
    }
}
```

## DEPLOYMENT CONFIGURATION:

### Docker Compose Setup:
```yaml
# docker-compose.kafka.yml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    volumes:
      - zk-data:/var/lib/zookeeper/data
      - zk-logs:/var/lib/zookeeper/log

  kafka-1:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka-1:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_LOG_SEGMENT_BYTES: 1073741824
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: false
    volumes:
      - kafka-1-data:/var/lib/kafka/data
    ports:
      - "9092:9092"

  kafka-connect:
    image: confluentinc/cp-kafka-connect:7.4.0
    depends_on:
      - kafka-1
    environment:
      CONNECT_BOOTSTRAP_SERVERS: kafka-1:29092
      CONNECT_REST_ADVERTISED_HOST_NAME: kafka-connect
      CONNECT_GROUP_ID: ghost-story-connect-group
      CONNECT_CONFIG_STORAGE_TOPIC: connect-configs
      CONNECT_OFFSET_STORAGE_TOPIC: connect-offsets
      CONNECT_STATUS_STORAGE_TOPIC: connect-status
      CONNECT_KEY_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_VALUE_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_PLUGIN_PATH: /usr/share/java,/usr/share/confluent-hub-components
    ports:
      - "8083:8083"
    volumes:
      - ./kafka-connect-plugins:/usr/share/confluent-hub-components

  schema-registry:
    image: confluentinc/cp-schema-registry:7.4.0
    depends_on:
      - kafka-1
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka-1:29092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
    ports:
      - "8081:8081"

volumes:
  zk-data:
  zk-logs:
  kafka-1-data:
  kafka-2-data:
  kafka-3-data:
```

### Production Deployment Scripts:
```bash
#!/bin/bash
# deploy-kafka-cluster.sh

# Set up environment
export KAFKA_CLUSTER_NAME="ghost-story-kafka"
export KAFKA_VERSION="7.4.0"
export ENVIRONMENT="production"

# Create Kafka topics
kafka-topics --create --topic ptt-new-posts --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092
kafka-topics --create --topic reddit-new-posts --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092
kafka-topics --create --topic bronze-ingestion --partitions 12 --replication-factor 3 --bootstrap-server localhost:9092
kafka-topics --create --topic processing-errors --partitions 3 --replication-factor 3 --bootstrap-server localhost:9092
kafka-topics --create --topic system-alerts --partitions 1 --replication-factor 3 --bootstrap-server localhost:9092

# Set up Kafka Connect connectors
curl -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d @postgresql-sink-connector.json

# Start monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

echo "Kafka cluster deployment completed successfully"
```

## MONITORING DASHBOARDS:

### Grafana Dashboard Configuration:
```json
{
  "dashboard": {
    "title": "Ghost Story Kafka Streaming",
    "panels": [
      {
        "title": "Message Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(kafka_producer_messages_sent_total[5m])",
            "legendFormat": "Messages Produced/sec"
          },
          {
            "expr": "rate(kafka_consumer_messages_consumed_total[5m])",
            "legendFormat": "Messages Consumed/sec"
          }
        ]
      },
      {
        "title": "Consumer Lag",
        "type": "graph",
        "targets": [
          {
            "expr": "kafka_consumer_lag_sum",
            "legendFormat": "Consumer Lag"
          }
        ]
      },
      {
        "title": "Topic Partition Distribution",
        "type": "table",
        "targets": [
          {
            "expr": "kafka_topic_partitions",
            "format": "table"
          }
        ]
      }
    ]
  }
}
```

## DISASTER RECOVERY:

### Backup and Recovery Procedures:
```python
class KafkaBackupManager:
    """Backup and recovery management for Kafka topics"""
    
    def __init__(self, kafka_config, backup_config):
        self.consumer = KafkaConsumer(**kafka_config)
        self.backup_config = backup_config
        
    async def backup_topic_data(self, topic_name, backup_path):
        """Backup topic data to external storage"""
        self.consumer.subscribe([topic_name])
        
        with open(f"{backup_path}/{topic_name}_{datetime.now().isoformat()}.jsonl", 'w') as backup_file:
            for message in self.consumer:
                backup_record = {
                    'topic': message.topic,
                    'partition': message.partition,
                    'offset': message.offset,
                    'key': message.key.decode('utf-8') if message.key else None,
                    'value': message.value.decode('utf-8'),
                    'timestamp': message.timestamp
                }
                backup_file.write(json.dumps(backup_record) + '\n')
    
    async def restore_topic_data(self, topic_name, backup_path):
        """Restore topic data from backup"""
        producer = KafkaProducer(**self.kafka_config)
        
        with open(f"{backup_path}/{topic_name}.jsonl", 'r') as backup_file:
            for line in backup_file:
                record = json.loads(line.strip())
                producer.send(
                    record['topic'],
                    key=record['key'].encode('utf-8') if record['key'] else None,
                    value=record['value'].encode('utf-8'),
                    partition=record['partition']
                )
        
        producer.flush()
```

## OTHER CONSIDERATIONS:
- **Message schema evolution** with backward compatibility using Schema Registry
- **Cross-region replication** for disaster recovery and global content distribution
- **Cost optimization** through intelligent topic retention and compression strategies
- **Capacity planning** for growth projection and resource scaling requirements
- **Integration testing** with comprehensive test suites for producer/consumer reliability
- **Documentation standards** including operational runbooks and troubleshooting guides
- **Team training** materials for Kafka administration and troubleshooting procedures
- **Compliance considerations** for data retention and privacy requirements in streaming data