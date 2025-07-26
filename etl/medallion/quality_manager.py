"""
Data Quality Manager - Great Expectations Integration
Implements comprehensive data quality validation for medallion architecture
"""

import asyncio
import asyncpg
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.config.config import CONFIG

# Great Expectations imports
try:
    import great_expectations as gx
    from great_expectations.core.batch import RuntimeBatchRequest
    from great_expectations.dataset import PandasDataset
    import pandas as pd
    GREAT_EXPECTATIONS_AVAILABLE = True
except ImportError:
    GREAT_EXPECTATIONS_AVAILABLE = False
    print("⚠️  Great Expectations not available - install great-expectations package")

# Alternative validation without Great Expectations
import re
from statistics import mean, median, stdev


@dataclass
class QualityCheckResult:
    """Result of a data quality check"""
    check_name: str
    success: bool
    expectation_type: str
    observed_value: Any
    expected_value: Any
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class LayerQualityReport:
    """Quality report for a medallion layer"""
    layer_name: str  # bronze, silver, gold
    total_checks: int
    passed_checks: int
    failed_checks: int
    success_rate: float
    check_results: List[QualityCheckResult]
    metadata: Dict[str, Any]
    processing_time_ms: int


class QualityManager:
    """
    Data Quality Manager for medallion architecture
    Integrates Great Expectations for comprehensive data validation
    """
    
    def __init__(self):
        """Initialize quality manager"""
        self.pool = None
        self.db_config = CONFIG["database"]
        self.ge_context = None
        self.expectations_dir = Path("examples/infrastructure/monitoring/data_quality/expectations")
        self.checkpoints_dir = Path("examples/infrastructure/monitoring/data_quality/checkpoints")
        
        # Create directories if they don't exist
        self.expectations_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Quality thresholds
        self.quality_thresholds = {
            'bronze_layer': {
                'min_success_rate': 0.90,  # 90% of checks must pass
                'max_null_percentage': 0.10,  # Max 10% null values
                'min_content_length': 50  # Minimum content length
            },
            'silver_layer': {
                'min_success_rate': 0.95,  # 95% of checks must pass
                'max_null_percentage': 0.05,  # Max 5% null values
                'min_quality_score': 0.5,  # Minimum quality score
                'max_chunks_per_story': 100  # Maximum chunks per story
            },
            'gold_layer': {
                'min_success_rate': 0.98,  # 98% of checks must pass
                'max_null_percentage': 0.02,  # Max 2% null values
                'min_metrics_freshness_hours': 24  # Metrics must be less than 24 hours old
            }
        }
        
        # Statistics tracking
        self.stats = {
            'total_quality_checks': 0,
            'total_validations': 0,
            'bronze_layer_checks': 0,
            'silver_layer_checks': 0,
            'gold_layer_checks': 0,
            'failed_validations': 0,
            'avg_processing_time': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize quality manager with database and Great Expectations"""
        try:
            print("🚀 Initializing Data Quality Manager...")
            
            # Initialize database connection pool
            self.pool = await asyncpg.create_pool(
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.database,
                user=self.db_config.username,
                password=self.db_config.password,
                min_size=self.db_config.min_connections,
                max_size=self.db_config.max_connections,
                command_timeout=60
            )
            print("✅ Database connection pool created")
            
            # Initialize Great Expectations if available
            if GREAT_EXPECTATIONS_AVAILABLE:
                try:
                    # Create Great Expectations context
                    context_root_dir = Path("examples/infrastructure/monitoring/data_quality")
                    context_root_dir.mkdir(parents=True, exist_ok=True)
                    
                    self.ge_context = gx.get_context(context_root_dir=str(context_root_dir))
                    print("✅ Great Expectations context initialized")
                    
                    # Setup datasource for PostgreSQL
                    await self._setup_datasource()
                    
                    # Create expectation suites
                    await self._create_expectation_suites()
                    
                except Exception as e:
                    print(f"⚠️  Great Expectations setup failed: {e}")
                    self.ge_context = None
            else:
                print("⚠️  Using fallback quality validation (Great Expectations not available)")
            
            return True
            
        except Exception as e:
            print(f"❌ Quality manager initialization failed: {e}")
            return False
    
    async def disconnect(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            print("Quality manager database connections closed")
    
    async def _setup_datasource(self):
        """Setup PostgreSQL datasource for Great Expectations"""
        if not self.ge_context:
            return
        
        try:
            # Create PostgreSQL datasource configuration
            datasource_config = {
                "name": "hauntbro_postgresql",
                "class_name": "Datasource",
                "execution_engine": {
                    "class_name": "SqlAlchemyExecutionEngine",
                    "connection_string": f"postgresql://{self.db_config.username}:{self.db_config.password}@{self.db_config.host}:{self.db_config.port}/{self.db_config.database}"
                },
                "data_connectors": {
                    "default_runtime_data_connector": {
                        "class_name": "RuntimeDataConnector",
                        "batch_identifiers": ["default_identifier_name"]
                    }
                }
            }
            
            # Add datasource to context
            self.ge_context.add_datasource(**datasource_config)
            print("✅ PostgreSQL datasource configured for Great Expectations")
            
        except Exception as e:
            print(f"⚠️  Datasource setup failed: {e}")
    
    async def _create_expectation_suites(self):
        """Create expectation suites for each medallion layer"""
        if not self.ge_context:
            return
        
        try:
            # Bronze layer expectations
            bronze_suite = self.ge_context.create_expectation_suite(
                expectation_suite_name="bronze_layer_suite",
                overwrite_existing=True
            )
            
            # Silver layer expectations
            silver_suite = self.ge_context.create_expectation_suite(
                expectation_suite_name="silver_layer_suite",
                overwrite_existing=True
            )
            
            # Gold layer expectations
            gold_suite = self.ge_context.create_expectation_suite(
                expectation_suite_name="gold_layer_suite",
                overwrite_existing=True
            )
            
            print("✅ Expectation suites created")
            
        except Exception as e:
            print(f"⚠️  Expectation suite creation failed: {e}")
    
    async def validate_bronze_layer(self, table_name: str = "bronze_stories") -> LayerQualityReport:
        """Validate bronze layer data quality"""
        start_time = datetime.now()
        layer_name = "bronze_layer"
        
        try:
            print(f"🔍 Validating {layer_name}...")
            
            if GREAT_EXPECTATIONS_AVAILABLE and self.ge_context:
                # Use Great Expectations for validation
                report = await self._validate_with_great_expectations(
                    table_name, "bronze_layer_suite", layer_name
                )
            else:
                # Use fallback validation
                report = await self._validate_bronze_fallback(table_name, layer_name)
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            report.processing_time_ms = processing_time_ms
            
            # Update statistics
            self.stats['bronze_layer_checks'] += 1
            self.stats['total_validations'] += 1
            if report.success_rate < self.quality_thresholds[layer_name]['min_success_rate']:
                self.stats['failed_validations'] += 1
            
            return report
            
        except Exception as e:
            print(f"❌ Bronze layer validation failed: {e}")
            return LayerQualityReport(
                layer_name=layer_name,
                total_checks=0,
                passed_checks=0,
                failed_checks=1,
                success_rate=0.0,
                check_results=[],
                metadata={'error': str(e)},
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def validate_silver_layer(self, table_name: str = "silver_story_chunks") -> LayerQualityReport:
        """Validate silver layer data quality"""
        start_time = datetime.now()
        layer_name = "silver_layer"
        
        try:
            print(f"🔍 Validating {layer_name}...")
            
            if GREAT_EXPECTATIONS_AVAILABLE and self.ge_context:
                # Use Great Expectations for validation
                report = await self._validate_with_great_expectations(
                    table_name, "silver_layer_suite", layer_name
                )
            else:
                # Use fallback validation
                report = await self._validate_silver_fallback(table_name, layer_name)
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            report.processing_time_ms = processing_time_ms
            
            # Update statistics
            self.stats['silver_layer_checks'] += 1
            self.stats['total_validations'] += 1
            if report.success_rate < self.quality_thresholds[layer_name]['min_success_rate']:
                self.stats['failed_validations'] += 1
            
            return report
            
        except Exception as e:
            print(f"❌ Silver layer validation failed: {e}")
            return LayerQualityReport(
                layer_name=layer_name,
                total_checks=0,
                passed_checks=0,
                failed_checks=1,
                success_rate=0.0,
                check_results=[],
                metadata={'error': str(e)},
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def validate_gold_layer(self, table_name: str = "gold_layer_metrics") -> LayerQualityReport:
        """Validate gold layer data quality"""
        start_time = datetime.now()
        layer_name = "gold_layer"
        
        try:
            print(f"🔍 Validating {layer_name}...")
            
            if GREAT_EXPECTATIONS_AVAILABLE and self.ge_context:
                # Use Great Expectations for validation
                report = await self._validate_with_great_expectations(
                    table_name, "gold_layer_suite", layer_name
                )
            else:
                # Use fallback validation
                report = await self._validate_gold_fallback(table_name, layer_name)
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            report.processing_time_ms = processing_time_ms
            
            # Update statistics
            self.stats['gold_layer_checks'] += 1
            self.stats['total_validations'] += 1
            if report.success_rate < self.quality_thresholds[layer_name]['min_success_rate']:
                self.stats['failed_validations'] += 1
            
            return report
            
        except Exception as e:
            print(f"❌ Gold layer validation failed: {e}")
            return LayerQualityReport(
                layer_name=layer_name,
                total_checks=0,
                passed_checks=0,
                failed_checks=1,
                success_rate=0.0,
                check_results=[],
                metadata={'error': str(e)},
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000)
            )
    
    async def _validate_with_great_expectations(self, table_name: str, suite_name: str, layer_name: str) -> LayerQualityReport:
        """Validate using Great Expectations"""
        try:
            # Create batch request
            batch_request = RuntimeBatchRequest(
                datasource_name="hauntbro_postgresql",
                data_connector_name="default_runtime_data_connector",
                data_asset_name=table_name,
                runtime_parameters={"query": f"SELECT * FROM {table_name} LIMIT 10000"},
                batch_identifiers={"default_identifier_name": "default_identifier"}
            )
            
            # Get validator
            validator = self.ge_context.get_validator(
                batch_request=batch_request,
                expectation_suite_name=suite_name
            )
            
            # Run validation
            validation_result = validator.validate()
            
            # Convert results to our format
            check_results = []
            passed_checks = 0
            failed_checks = 0
            
            for result in validation_result.results:
                success = result.success
                if success:
                    passed_checks += 1
                else:
                    failed_checks += 1
                
                check_result = QualityCheckResult(
                    check_name=result.expectation_config.expectation_type,
                    success=success,
                    expectation_type=result.expectation_config.expectation_type,
                    observed_value=result.result.get('observed_value'),
                    expected_value=result.expectation_config.kwargs,
                    details=result.result,
                    timestamp=datetime.now(timezone.utc)
                )
                check_results.append(check_result)
            
            total_checks = passed_checks + failed_checks
            success_rate = passed_checks / max(total_checks, 1)
            
            return LayerQualityReport(
                layer_name=layer_name,
                total_checks=total_checks,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                success_rate=success_rate,
                check_results=check_results,
                metadata={
                    'validation_result_identifier': validation_result.meta.get('run_id'),
                    'suite_name': suite_name,
                    'table_name': table_name
                },
                processing_time_ms=0  # Will be set by caller
            )
            
        except Exception as e:
            raise Exception(f"Great Expectations validation failed: {e}")
    
    async def _validate_bronze_fallback(self, table_name: str, layer_name: str) -> LayerQualityReport:
        """Fallback validation for bronze layer without Great Expectations"""
        check_results = []
        
        async with self.pool.acquire() as conn:
            # Check 1: Table exists and has data
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            total_rows = await conn.fetchval(count_query)
            
            check_results.append(QualityCheckResult(
                check_name="table_has_data",
                success=total_rows > 0,
                expectation_type="expect_table_row_count_to_be_between",
                observed_value=total_rows,
                expected_value={"min_value": 1},
                details={"row_count": total_rows},
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 2: Content length validation
            content_length_query = f"""
            SELECT 
                AVG(LENGTH(content)) as avg_length,
                MIN(LENGTH(content)) as min_length,
                COUNT(CASE WHEN LENGTH(content) < {self.quality_thresholds[layer_name]['min_content_length']} THEN 1 END) as short_content_count
            FROM {table_name}
            WHERE content IS NOT NULL
            """
            
            length_stats = await conn.fetchrow(content_length_query)
            short_content_rate = length_stats['short_content_count'] / max(total_rows, 1)
            
            check_results.append(QualityCheckResult(
                check_name="content_length_validation",
                success=short_content_rate < 0.1,  # Less than 10% short content
                expectation_type="expect_column_values_to_be_between",
                observed_value=short_content_rate,
                expected_value={"max_value": 0.1},
                details=dict(length_stats),
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 3: Null value validation
            null_check_query = f"""
            SELECT 
                COUNT(CASE WHEN title IS NULL THEN 1 END)::float / COUNT(*) as title_null_rate,
                COUNT(CASE WHEN content IS NULL THEN 1 END)::float / COUNT(*) as content_null_rate,
                COUNT(CASE WHEN source IS NULL THEN 1 END)::float / COUNT(*) as source_null_rate
            FROM {table_name}
            """
            
            null_stats = await conn.fetchrow(null_check_query)
            max_null_rate = max(null_stats['title_null_rate'], null_stats['content_null_rate'], null_stats['source_null_rate'])
            
            check_results.append(QualityCheckResult(
                check_name="null_value_validation",
                success=max_null_rate < self.quality_thresholds[layer_name]['max_null_percentage'],
                expectation_type="expect_column_values_to_not_be_null",
                observed_value=max_null_rate,
                expected_value={"max_null_rate": self.quality_thresholds[layer_name]['max_null_percentage']},
                details=dict(null_stats),
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 4: Duplicate detection
            duplicate_query = f"""
            SELECT COUNT(*) - COUNT(DISTINCT source_url) as duplicates
            FROM {table_name}
            WHERE source_url IS NOT NULL
            """
            
            duplicates = await conn.fetchval(duplicate_query)
            duplicate_rate = duplicates / max(total_rows, 1)
            
            check_results.append(QualityCheckResult(
                check_name="duplicate_detection",
                success=duplicate_rate < 0.05,  # Less than 5% duplicates
                expectation_type="expect_compound_columns_to_be_unique",
                observed_value=duplicate_rate,
                expected_value={"max_duplicate_rate": 0.05},
                details={"duplicates": duplicates, "total_rows": total_rows},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Calculate overall success rate
        passed_checks = sum(1 for check in check_results if check.success)
        failed_checks = len(check_results) - passed_checks
        success_rate = passed_checks / len(check_results)
        
        return LayerQualityReport(
            layer_name=layer_name,
            total_checks=len(check_results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            success_rate=success_rate,
            check_results=check_results,
            metadata={"validation_method": "fallback", "table_name": table_name},
            processing_time_ms=0
        )
    
    async def _validate_silver_fallback(self, table_name: str, layer_name: str) -> LayerQualityReport:
        """Fallback validation for silver layer"""
        check_results = []
        
        async with self.pool.acquire() as conn:
            # Check 1: Chunk quality scores
            quality_query = f"""
            SELECT 
                AVG(chunk_quality_score) as avg_quality,
                MIN(chunk_quality_score) as min_quality,
                COUNT(CASE WHEN chunk_quality_score < {self.quality_thresholds[layer_name]['min_quality_score']} THEN 1 END) as low_quality_count,
                COUNT(*) as total_chunks
            FROM {table_name}
            WHERE chunk_quality_score IS NOT NULL
            """
            
            quality_stats = await conn.fetchrow(quality_query)
            low_quality_rate = quality_stats['low_quality_count'] / max(quality_stats['total_chunks'], 1)
            
            check_results.append(QualityCheckResult(
                check_name="chunk_quality_validation",
                success=quality_stats['avg_quality'] >= self.quality_thresholds[layer_name]['min_quality_score'],
                expectation_type="expect_column_mean_to_be_between",
                observed_value=quality_stats['avg_quality'],
                expected_value={"min_value": self.quality_thresholds[layer_name]['min_quality_score']},
                details=dict(quality_stats),
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 2: Embedding completeness
            embedding_query = f"""
            SELECT 
                COUNT(CASE WHEN content_embedding IS NULL OR content_embedding = '' THEN 1 END)::float / COUNT(*) as missing_content_embedding_rate,
                COUNT(CASE WHEN search_embedding IS NULL OR search_embedding = '' THEN 1 END)::float / COUNT(*) as missing_search_embedding_rate
            FROM {table_name}
            """
            
            embedding_stats = await conn.fetchrow(embedding_query)
            max_missing_rate = max(embedding_stats['missing_content_embedding_rate'], embedding_stats['missing_search_embedding_rate'])
            
            check_results.append(QualityCheckResult(
                check_name="embedding_completeness",
                success=max_missing_rate < 0.1,  # Less than 10% missing embeddings
                expectation_type="expect_column_values_to_not_be_null",
                observed_value=max_missing_rate,
                expected_value={"max_missing_rate": 0.1},
                details=dict(embedding_stats),
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 3: Chunks per story validation
            chunks_per_story_query = f"""
            SELECT 
                AVG(chunk_count) as avg_chunks_per_story,
                MAX(chunk_count) as max_chunks_per_story,
                COUNT(CASE WHEN chunk_count > {self.quality_thresholds[layer_name]['max_chunks_per_story']} THEN 1 END) as stories_with_too_many_chunks
            FROM (
                SELECT story_id, COUNT(*) as chunk_count
                FROM {table_name}
                GROUP BY story_id
            ) chunk_counts
            """
            
            chunk_stats = await conn.fetchrow(chunk_stats_query)
            
            check_results.append(QualityCheckResult(
                check_name="chunks_per_story_validation",
                success=chunk_stats['max_chunks_per_story'] <= self.quality_thresholds[layer_name]['max_chunks_per_story'],
                expectation_type="expect_column_max_to_be_between",
                observed_value=chunk_stats['max_chunks_per_story'],
                expected_value={"max_value": self.quality_thresholds[layer_name]['max_chunks_per_story']},
                details=dict(chunk_stats),
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 4: Language consistency
            language_query = f"""
            SELECT 
                processing_language,
                COUNT(*) as count
            FROM {table_name}
            WHERE processing_language IS NOT NULL
            GROUP BY processing_language
            """
            
            language_stats = await conn.fetch(language_query)
            valid_languages = {'zh', 'en', 'mixed', 'unknown'}
            invalid_languages = [row['processing_language'] for row in language_stats 
                               if row['processing_language'] not in valid_languages]
            
            check_results.append(QualityCheckResult(
                check_name="language_consistency",
                success=len(invalid_languages) == 0,
                expectation_type="expect_column_values_to_be_in_set",
                observed_value=invalid_languages,
                expected_value={"value_set": list(valid_languages)},
                details={"language_distribution": dict(language_stats)},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Calculate overall success rate
        passed_checks = sum(1 for check in check_results if check.success)
        failed_checks = len(check_results) - passed_checks
        success_rate = passed_checks / len(check_results)
        
        return LayerQualityReport(
            layer_name=layer_name,
            total_checks=len(check_results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            success_rate=success_rate,
            check_results=check_results,
            metadata={"validation_method": "fallback", "table_name": table_name},
            processing_time_ms=0
        )
    
    async def _validate_gold_fallback(self, table_name: str, layer_name: str) -> LayerQualityReport:
        """Fallback validation for gold layer"""
        check_results = []
        
        async with self.pool.acquire() as conn:
            # Check 1: Data freshness
            freshness_query = f"""
            SELECT 
                MAX(created_at) as latest_metric,
                AVG(data_freshness_minutes) as avg_freshness_minutes
            FROM {table_name}
            """
            
            freshness_stats = await conn.fetchrow(freshness_query)
            if freshness_stats['latest_metric']:
                hours_since_latest = (datetime.now(timezone.utc) - freshness_stats['latest_metric']).total_seconds() / 3600
            else:
                hours_since_latest = float('inf')
            
            check_results.append(QualityCheckResult(
                check_name="data_freshness",
                success=hours_since_latest <= self.quality_thresholds[layer_name]['min_metrics_freshness_hours'],
                expectation_type="expect_column_values_to_be_recent",
                observed_value=hours_since_latest,
                expected_value={"max_hours": self.quality_thresholds[layer_name]['min_metrics_freshness_hours']},
                details=dict(freshness_stats) if freshness_stats else {},
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 2: Metric completeness
            completeness_query = f"""
            SELECT 
                COUNT(CASE WHEN total_stories_processed IS NULL THEN 1 END)::float / COUNT(*) as missing_stories_rate,
                COUNT(CASE WHEN avg_quality_score IS NULL THEN 1 END)::float / COUNT(*) as missing_quality_rate,
                COUNT(CASE WHEN total_embeddings_cost IS NULL THEN 1 END)::float / COUNT(*) as missing_cost_rate
            FROM {table_name}
            """
            
            completeness_stats = await conn.fetchrow(completeness_query)
            max_missing_rate = max(
                completeness_stats['missing_stories_rate'],
                completeness_stats['missing_quality_rate'],
                completeness_stats['missing_cost_rate']
            )
            
            check_results.append(QualityCheckResult(
                check_name="metric_completeness",
                success=max_missing_rate < self.quality_thresholds[layer_name]['max_null_percentage'],
                expectation_type="expect_column_values_to_not_be_null",
                observed_value=max_missing_rate,
                expected_value={"max_null_rate": self.quality_thresholds[layer_name]['max_null_percentage']},
                details=dict(completeness_stats),
                timestamp=datetime.now(timezone.utc)
            ))
            
            # Check 3: Business metric ranges
            range_query = f"""
            SELECT 
                MIN(conversion_rate) as min_conversion_rate,
                MAX(conversion_rate) as max_conversion_rate,
                AVG(avg_quality_score) as avg_quality_score
            FROM {table_name}
            WHERE conversion_rate IS NOT NULL AND avg_quality_score IS NOT NULL
            """
            
            range_stats = await conn.fetchrow(range_query)
            
            # Conversion rate should be between 0 and 1
            valid_conversion_range = (
                range_stats and
                range_stats['min_conversion_rate'] >= 0 and 
                range_stats['max_conversion_rate'] <= 1
            )
            
            check_results.append(QualityCheckResult(
                check_name="business_metric_ranges",
                success=valid_conversion_range,
                expectation_type="expect_column_values_to_be_between",
                observed_value={
                    "min_conversion": range_stats['min_conversion_rate'] if range_stats else None,
                    "max_conversion": range_stats['max_conversion_rate'] if range_stats else None
                },
                expected_value={"min_value": 0, "max_value": 1},
                details=dict(range_stats) if range_stats else {},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Calculate overall success rate
        passed_checks = sum(1 for check in check_results if check.success)
        failed_checks = len(check_results) - passed_checks
        success_rate = passed_checks / len(check_results)
        
        return LayerQualityReport(
            layer_name=layer_name,
            total_checks=len(check_results),
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            success_rate=success_rate,
            check_results=check_results,
            metadata={"validation_method": "fallback", "table_name": table_name},
            processing_time_ms=0
        )
    
    async def validate_all_layers(self) -> Dict[str, LayerQualityReport]:
        """Validate all medallion layers"""
        print("🔍 Running comprehensive quality validation across all layers...")
        
        results = {}
        
        # Validate each layer
        try:
            results['bronze'] = await self.validate_bronze_layer()
        except Exception as e:
            print(f"❌ Bronze layer validation failed: {e}")
        
        try:
            results['silver'] = await self.validate_silver_layer()
        except Exception as e:
            print(f"❌ Silver layer validation failed: {e}")
        
        try:
            results['gold'] = await self.validate_gold_layer()
        except Exception as e:
            print(f"❌ Gold layer validation failed: {e}")
        
        # Generate summary
        total_checks = sum(report.total_checks for report in results.values())
        total_passed = sum(report.passed_checks for report in results.values())
        overall_success_rate = total_passed / max(total_checks, 1)
        
        print(f"📊 Overall Quality Summary:")
        print(f"   Total checks: {total_checks}")
        print(f"   Passed: {total_passed}")
        print(f"   Success rate: {overall_success_rate:.2%}")
        
        for layer, report in results.items():
            status = "✅" if report.success_rate >= 0.9 else "⚠️" if report.success_rate >= 0.7 else "❌"
            print(f"   {status} {layer.capitalize()}: {report.success_rate:.2%} ({report.passed_checks}/{report.total_checks})")
        
        return results
    
    def get_quality_stats(self) -> Dict:
        """Get quality validation statistics"""
        return {
            'quality_manager_type': 'great_expectations_integrated',
            'great_expectations_available': GREAT_EXPECTATIONS_AVAILABLE,
            'validation_stats': self.stats,
            'quality_thresholds': self.quality_thresholds,
            'overall_success_rate': (
                (self.stats['total_validations'] - self.stats['failed_validations']) / 
                max(self.stats['total_validations'], 1)
            )
        }


# CLI interface for testing
async def main():
    """Main CLI interface for testing quality manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Data Quality Manager")
    parser.add_argument('--layer', choices=['bronze', 'silver', 'gold', 'all'], 
                       default='all', help='Layer to validate')
    parser.add_argument('--stats', action='store_true', help='Show quality statistics')
    
    args = parser.parse_args()
    
    manager = QualityManager()
    
    try:
        await manager.initialize()
        
        if args.stats:
            stats = manager.get_quality_stats()
            print(f"📊 Quality Statistics: {json.dumps(stats, indent=2)}")
        
        if args.layer == 'all':
            results = await manager.validate_all_layers()
            
            print(f"\n📋 Detailed Results:")
            for layer, report in results.items():
                print(f"\n{layer.upper()} LAYER:")
                print(f"  Success rate: {report.success_rate:.2%}")
                print(f"  Processing time: {report.processing_time_ms}ms")
                
                # Show failed checks
                failed_checks = [check for check in report.check_results if not check.success]
                if failed_checks:
                    print(f"  Failed checks:")
                    for check in failed_checks:
                        print(f"    ❌ {check.check_name}: {check.observed_value}")
        else:
            # Validate single layer
            layer_method = getattr(manager, f'validate_{args.layer}_layer')
            report = await layer_method()
            
            print(f"\n📋 {args.layer.upper()} Layer Results:")
            print(f"  Success rate: {report.success_rate:.2%}")
            print(f"  Checks: {report.passed_checks}/{report.total_checks}")
            print(f"  Processing time: {report.processing_time_ms}ms")
        
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Quality manager error: {e}")
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    asyncio.run(main())