"""
Bronze Layer Processor Operator
Custom Airflow operator for bronze layer data ingestion
"""

from typing import Any, Dict, Optional, Sequence
from airflow.models import BaseOperator
from airflow.utils.context import Context
from airflow.utils.decorators import apply_defaults
import asyncio
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from etl.medallion.bronze_processor import BronzeProcessor


class BronzeProcessorOperator(BaseOperator):
    """
    Custom Airflow operator for bronze layer processing
    
    Handles raw data ingestion from Reddit and PTT sources into the bronze layer
    of the medallion architecture with immutable data preservation.
    """
    
    template_fields: Sequence[str] = ('source_platform', 'target_date')
    template_ext: Sequence[str] = ()
    ui_color = '#CD853F'  # Bronze color
    
    @apply_defaults
    def __init__(
        self,
        source_platform: str,
        batch_size: int = 100,
        target_date: Optional[str] = None,
        force_refresh: bool = False,
        *args,
        **kwargs
    ):
        """
        Initialize Bronze Processor Operator
        
        Args:
            source_platform: Platform to process ('reddit', 'ptt', or 'all')
            batch_size: Number of stories to process per batch
            target_date: Specific date to process (defaults to execution date)
            force_refresh: Whether to reprocess existing data
        """
        super().__init__(*args, **kwargs)
        self.source_platform = source_platform
        self.batch_size = batch_size
        self.target_date = target_date
        self.force_refresh = force_refresh
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute bronze layer processing"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting bronze layer processing for {self.source_platform}")
        self.log.info(f"Batch size: {self.batch_size}, Target date: {target_date}")
        
        # Generate ETL run ID
        etl_run_id = f"bronze_{self.source_platform}_{execution_date}_{context.get('task_instance').try_number}"
        
        # Run bronze processing asynchronously
        result = asyncio.run(self._run_bronze_processing(etl_run_id, target_date))
        
        self.log.info(f"Bronze processing completed: {result}")
        
        # Store results in XCom for downstream tasks
        context['task_instance'].xcom_push(key='bronze_result', value=result)
        context['task_instance'].xcom_push(key='etl_run_id', value=etl_run_id)
        
        return result
    
    async def _run_bronze_processing(self, etl_run_id: str, target_date: str) -> Dict[str, Any]:
        """Run the actual bronze processing"""
        processor = BronzeProcessor()
        
        try:
            # Initialize processor
            initialized = await processor.initialize()
            if not initialized:
                raise Exception("Failed to initialize bronze processor")
            
            # Process based on platform
            if self.source_platform == 'all':
                # Process all platforms
                results = {}
                for platform in ['reddit', 'ptt']:
                    platform_result = await processor.process_platform_data(
                        platform=platform,
                        batch_size=self.batch_size,
                        etl_run_id=f"{etl_run_id}_{platform}",
                        force_refresh=self.force_refresh
                    )
                    results[platform] = platform_result
                
                # Aggregate results
                total_processed = sum(r.get('stories_processed', 0) for r in results.values())
                total_errors = sum(r.get('processing_errors', 0) for r in results.values())
                
                result = {
                    'success': all(r.get('success', False) for r in results.values()),
                    'platform_results': results,
                    'total_stories_processed': total_processed,
                    'total_processing_errors': total_errors,
                    'etl_run_id': etl_run_id,
                    'processing_date': target_date
                }
            else:
                # Process single platform
                platform_result = await processor.process_platform_data(
                    platform=self.source_platform,
                    batch_size=self.batch_size,
                    etl_run_id=etl_run_id,
                    force_refresh=self.force_refresh
                )
                
                result = {
                    'success': platform_result.get('success', False),
                    'stories_processed': platform_result.get('stories_processed', 0),
                    'processing_errors': platform_result.get('processing_errors', 0),
                    'processing_time_ms': platform_result.get('processing_time_ms', 0),
                    'etl_run_id': etl_run_id,
                    'processing_date': target_date,
                    'platform': self.source_platform
                }
            
            return result
            
        except Exception as e:
            self.log.error(f"Bronze processing failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'etl_run_id': etl_run_id,
                'processing_date': target_date,
                'platform': self.source_platform
            }
        finally:
            await processor.disconnect()
    
    def on_kill(self) -> None:
        """Handle task termination"""
        self.log.info("Bronze processor operator killed")


class BronzeQualityCheckOperator(BaseOperator):
    """
    Operator for bronze layer quality validation
    """
    
    template_fields: Sequence[str] = ('target_date',)
    ui_color = '#DEB887'  # Light bronze color
    
    @apply_defaults
    def __init__(
        self,
        quality_threshold: float = 0.9,
        target_date: Optional[str] = None,
        fail_on_quality_issues: bool = True,
        *args,
        **kwargs
    ):
        """
        Initialize Bronze Quality Check Operator
        
        Args:
            quality_threshold: Minimum quality score required
            target_date: Date to validate (defaults to execution date)
            fail_on_quality_issues: Whether to fail task on quality issues
        """
        super().__init__(*args, **kwargs)
        self.quality_threshold = quality_threshold
        self.target_date = target_date
        self.fail_on_quality_issues = fail_on_quality_issues
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute bronze layer quality validation"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting bronze layer quality validation for {target_date}")
        
        # Run quality check
        result = asyncio.run(self._run_quality_check(target_date))
        
        # Check if we should fail the task
        if self.fail_on_quality_issues and not result['success']:
            raise Exception(f"Bronze layer quality check failed: {result.get('error_message')}")
        
        self.log.info(f"Bronze quality check completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='bronze_quality_result', value=result)
        
        return result
    
    async def _run_quality_check(self, target_date: str) -> Dict[str, Any]:
        """Run the actual quality validation"""
        from etl.medallion.quality_manager import QualityManager
        
        quality_manager = QualityManager()
        
        try:
            # Initialize quality manager
            initialized = await quality_manager.initialize()
            if not initialized:
                raise Exception("Failed to initialize quality manager")
            
            # Run bronze layer validation
            quality_report = await quality_manager.validate_bronze_layer()
            
            # Evaluate results
            success = quality_report.success_rate >= self.quality_threshold
            
            result = {
                'success': success,
                'quality_score': quality_report.success_rate,
                'threshold': self.quality_threshold,
                'total_checks': quality_report.total_checks,
                'passed_checks': quality_report.passed_checks,
                'failed_checks': quality_report.failed_checks,
                'processing_time_ms': quality_report.processing_time_ms,
                'validation_date': target_date,
                'layer': 'bronze'
            }
            
            if not success:
                result['error_message'] = f"Quality score {quality_report.success_rate:.2f} below threshold {self.quality_threshold}"
                
                # Add details about failed checks
                failed_check_details = [
                    f"{check.check_name}: {check.observed_value}"
                    for check in quality_report.check_results
                    if not check.success
                ]
                result['failed_check_details'] = failed_check_details
            
            return result
            
        except Exception as e:
            self.log.error(f"Bronze quality check failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'validation_date': target_date,
                'layer': 'bronze'
            }
        finally:
            await quality_manager.disconnect()