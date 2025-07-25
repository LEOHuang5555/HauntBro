
## FEATURE: Medallion Architecture ETL Pipeline (Bronze → Silver → Gold)

Implement a comprehensive ETL system following the medallion model that transforms raw ghost story data through bronze, silver, and gold layers with quality assurance, monitoring, and business intelligence capabilities. The system should process both PTT (Traditional Chinese) and Reddit (English) content through separate but coordinated pipelines.

## PRIMARY FUNCTIONALITY:
- **Bronze Layer:** Raw data ingestion and immutable storage preservation from PTT and Reddit scrapers
- **Silver Layer:** Data cleaning, chunking with DeepSeek (Chinese) and LLaMA (English), embedding generation, and quality scoring
- **Gold Layer:** Business analytics aggregations, user behavior insights, and predictive analytics
- **Airflow DAG orchestration** for all ETL processes with dependency management
- **Data quality monitoring** and validation at each medallion layer transition
- **Error handling and data lineage tracking** throughout the entire pipeline
- **Real-time processing** for streaming data from Kafka and batch processing for historical data


## MEDALLION LAYER SPECIFICATIONS:

### Bronze Layer (Raw Data Preservation):
- **Direct ingestion** from PTT Marvel and Reddit scrapers with zero transformation
- **Complete metadata preservation** including timestamps, source URLs, raw HTML, HTTP headers
- **Immutable storage** with audit trail and version tracking
- **Schema evolution support** for changing source formats over time
- **Kafka stream integration** for real-time ingestion with exactly-once semantics
- **Data partitioning** by source (PTT/Reddit) and date for efficient querying
- **Duplicate detection** at ingestion level to prevent reprocessing

### Silver Layer (Processed & Enriched Data):
- **Content cleaning and standardization** with language-specific processing
- **Multi-language text processing** optimized for Traditional Chinese and English
- **Intelligent story chunking** using DeepSeek for Chinese content and LLaMA for English content
- **Embedding generation** with cost-optimized strategy (OpenAI vs open-source alternatives)
- **Quality scoring and content classification** with ML-based quality assessment
- **Duplicate detection and deduplication** using content similarity algorithms
- **Data validation and quality checks** with comprehensive error reporting
- **Metadata enrichment** including reading time estimation, complexity scoring, and theme detection

### Gold Layer (Business Intelligence):
- **User behavior analytics aggregations** including reading patterns, engagement metrics, and conversion funnels
- **Content performance metrics** and trending analysis with predictive insights
- **Search pattern analysis** and optimization insights for improving user experience
- **Revenue and conversion funnel analytics** for freemium model optimization
- **A/B testing results** and experiment tracking for product decisions
- **Predictive analytics** for content recommendation and user segmentation
- **Cross-platform insights** combining PTT and Reddit data for comprehensive analysis

## TECHNICAL REQUIREMENTS:
- **Apache Airflow 2.5+** with custom operators and comprehensive DAG dependency management
- **DBT (Data Build Tool)** for SQL transformations with version control and testing
- **Great Expectations** for data quality testing and anomaly detection
- **Apache Spark** or pandas for large-scale data processing and transformation
- **Vector database integration** (pgvector for PostgreSQL) for embedding storage and similarity search
- **Monitoring with Grafana and Prometheus** for real-time pipeline health tracking
- **Error tracking with Sentry integration** for comprehensive error management
- **Poetry dependency management** with virtual environment isolation
- **Docker containerization** for consistent deployment across environments

## ETL PIPELINE DAGS:

### PTT_ETL_DAG (Traditional Chinese Processing):
- **Bronze ingestion** from PTT scraper output with Traditional Chinese encoding handling
- **Silver processing** with DeepSeek chunking and contextual understanding
- **Traditional Chinese text normalization** including character conversion and cleaning
- **Quality scoring and categorization** based on PTT-specific content patterns
- **Gold layer aggregation** for PTT-specific analytics and user behavior insights
- **Error handling** for Traditional Chinese encoding issues and cultural context processing

### Reddit_ETL_DAG (English Processing):
- **Bronze ingestion** from Reddit scraper output with subreddit-specific handling
- **Silver processing** with LLaMA chunking and narrative structure preservation
- **English text processing and standardization** including grammar and sentiment analysis
- **Quality scoring and subreddit classification** with engagement-based metrics
- **Gold layer aggregation** for Reddit-specific analytics and community insights
- **Error handling** for Reddit API rate limits and content format variations

### Cross_Platform_Analytics_DAG (Combined Analysis):
- **Combined analysis** across PTT and Reddit data with cultural context awareness
- **User behavior pattern analysis** for cross-platform user journeys
- **Content similarity and recommendation processing** using multilingual embeddings
- **Business metrics calculation** including revenue attribution and conversion tracking
- **Predictive modeling** for user lifetime value and churn prediction
- **Comparative analytics** between Chinese and English content performance

## CHUNKING & EMBEDDING STRATEGY:

### PTT Content (Traditional Chinese):
- **DeepSeek model integration** for contextual understanding of Traditional Chinese ghost stories
- **Optimal chunk size:** 200-500 Traditional Chinese characters with semantic overlap
- **Semantic boundary detection** for story coherence and narrative flow preservation
- **Cultural context preservation** in chunking including folklore references and cultural nuances
- **Traditional Chinese specific processing** including character normalization and cultural entity recognition

### Reddit Content (English):
- **LLaMA 4 model integration** for contextual understanding of English narrative structure
- **Optimal chunk size:** 100-300 words with paragraph-aware overlap
- **Paragraph and narrative structure preservation** maintaining story flow and character development
- **Sentiment and theme-aware chunking** for emotional coherence within chunks
- **English-specific processing** including slang detection and cultural reference handling

### Embedding Generation Strategy:
- **Cost comparison framework:** OpenAI embeddings vs open-source alternatives (sentence-transformers, all-MiniLM)
- **Batch processing optimization** for cost efficiency and throughput maximization
- **Vector dimension optimization** (768, 1024, or 1536) based on performance vs storage trade-offs
- **Embedding quality validation** with semantic similarity testing and benchmark evaluation
- **Multilingual embedding alignment** for cross-language similarity search capabilities

## DATA QUALITY FRAMEWORK:
- **Automated data validation** at each medallion layer transition with comprehensive rule sets
- **Quality metrics tracking** including completeness, accuracy, consistency, and timeliness
- **Anomaly detection** for unusual data patterns, content quality drops, and processing failures
- **Data profiling and statistical analysis** with trend monitoring and alerting
- **Quality dashboards and alerting** with real-time monitoring and automated remediation
- **Data lineage visualization** showing transformation history and dependency tracking

## USER STORIES:
- As a **data engineer**, I can monitor ETL pipeline health, performance metrics, and data quality scores in real-time
- As a **business analyst**, I can access clean, processed data for insights generation and decision making
- As a **developer**, I can trace data lineage from raw ingestion to final business metrics
- As an **admin**, I receive immediate alerts for data quality issues, pipeline failures, or processing anomalies
- As a **user**, I benefit from improved search relevance and recommendations through processed data
- As a **product manager**, I can analyze user behavior patterns and content performance across both platforms
- As a **data scientist**, I can access high-quality features for machine learning model development

## SUCCESS CRITERIA:
- **ETL processing latency:** <2 hours for daily batch processing, <15 minutes for real-time updates
- **Data quality score:** >95% across all medallion layers with automated quality assurance
- **Pipeline uptime:** >99.5% with automated recovery and minimal manual intervention
- **Cost optimization:** <$200/month for embedding generation and cloud infrastructure
- **Processing throughput:** 10K+ stories per hour during peak processing periods
- **Data freshness:** <30 minutes from source to gold layer for real-time content
- **Storage efficiency:** <50% storage growth through deduplication and compression

## PERFORMANCE REQUIREMENTS:
- **Concurrent processing:** Support 100+ concurrent Airflow tasks without resource contention
- **Memory optimization:** <8GB memory usage per processing worker
- **Storage optimization:** Partitioned storage with automatic archiving of old data
- **Query performance:** <1 second for gold layer analytics queries with proper indexing
- **Scalability:** Auto-scaling based on processing queue depth and resource utilization
- **Fault tolerance:** Automatic retry with exponential backoff for transient failures

## MONITORING & ALERTING:
- **Real-time pipeline monitoring** with Grafana dashboards showing processing rates and queue depths
- **Email notifications** for critical failures, data quality issues, and SLA breaches
- **Slack integration** for team alerts and automated incident response
- **Performance metrics tracking** including processing times, error rates, and resource utilization
- **Cost monitoring** for cloud resources, AI model usage, and overall pipeline expenses
- **Data drift detection** for changes in content patterns or source format modifications

## INTEGRATION POINTS:
- **Kafka streaming integration** for real-time bronze layer ingestion with exactly-once processing
- **Vector database integration** for embedding storage and similarity search capabilities
- **User analytics system** for behavioral data collection and analysis
- **Search engine integration** for improved relevance and recommendation features
- **Freemium system integration** for usage analytics and conversion optimization
- **Content moderation system** for quality control and inappropriate content filtering

## ERROR HANDLING & RECOVERY:
- **Comprehensive error classification** with automatic vs manual intervention routing
- **Automatic retry mechanisms** with exponential backoff and circuit breaker patterns
- **Dead letter queues** for failed processing attempts with manual review workflows
- **Data corruption detection** with automatic rollback and reprocessing capabilities
- **Partial failure handling** allowing pipeline continuation despite individual task failures
- **Disaster recovery procedures** with backup data sources and emergency processing modes

## COMPLIANCE & SECURITY:
- **GDPR compliance** for user data processing with proper consent tracking
- **Data retention policies** for different medallion layers with automated cleanup
- **Access control** with role-based permissions for different user types
- **Data encryption** at rest and in transit for sensitive information
- **Audit logging** for all data transformations and access patterns
- **Privacy preservation** techniques for user behavior analytics

## TESTING STRATEGY:
- **Unit tests** for all transformation functions with comprehensive edge case coverage
- **Integration tests** for DAG execution and data flow validation
- **Data quality tests** using Great Expectations with automated failure notifications
- **Performance tests** for processing throughput and resource utilization
- **End-to-end tests** for complete pipeline execution from bronze to gold
- **Regression tests** for ensuring consistent output quality across code changes

## DEPLOYMENT & INFRASTRUCTURE:
- **Docker containerization** with multi-stage builds for optimization
- **Kubernetes deployment** with auto-scaling and resource management
- **Infrastructure as Code** using Terraform for reproducible deployments
- **CI/CD pipeline** with automated testing and deployment validation
- **Environment separation** (dev/staging/prod) with appropriate data isolation
- **Blue-green deployment** strategy for zero-downtime updates

## OTHER CONSIDERATIONS:
- **Multi-language support** with proper encoding handling and cultural context preservation
- **Time zone handling** for global data sources and user analytics
- **Data archival strategy** with cost-optimized long-term storage
- **Capacity planning** for growth projection and resource scaling
- **Documentation standards** including data dictionaries and transformation logic
- **Team collaboration** tools for shared development and debugging procedures
- **Cost optimization strategies** including resource scheduling and usage monitoring
- **Future extensibility** for additional data sources and processing requirements