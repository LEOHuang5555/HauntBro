"""
Silver Layer Processor Operator
Custom Airflow operator for silver layer language-specific processing
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

from etl.medallion.silver_processor import SilverProcessor


class SilverProcessorOperator(BaseOperator):
    """
    Custom Airflow operator for silver layer processing
    
    Handles language-specific content processing, chunking, and embedding generation
    for the silver layer of the medallion architecture.
    """
    
    template_fields: Sequence[str] = ('target_date', 'quality_threshold')
    template_ext: Sequence[str] = ()
    ui_color = '#C0C0C0'  # Silver color
    
    @apply_defaults
    def __init__(
        self,
        batch_size: int = 50,
        quality_threshold: float = 0.5,
        target_date: Optional[str] = None,
        max_concurrent_tasks: int = 3,
        embedding_strategy: str = 'cost_optimized',
        *args,
        **kwargs
    ):
        """
        Initialize Silver Processor Operator
        
        Args:
            batch_size: Number of stories to process per batch
            quality_threshold: Minimum quality score for processing
            target_date: Specific date to process (defaults to execution date)
            max_concurrent_tasks: Maximum concurrent processing tasks
            embedding_strategy: Embedding generation strategy
        """
        super().__init__(*args, **kwargs)
        self.batch_size = batch_size
        self.quality_threshold = quality_threshold
        self.target_date = target_date
        self.max_concurrent_tasks = max_concurrent_tasks
        self.embedding_strategy = embedding_strategy
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute silver layer processing"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        # Get bronze processing results from XCom if available
        bronze_result = context['task_instance'].xcom_pull(
            task_ids='bronze_layer.process_reddit_stories',
            key='bronze_result'
        ) or context['task_instance'].xcom_pull(
            task_ids='bronze_layer.process_ptt_stories',
            key='bronze_result'
        )
        
        etl_run_id = context['task_instance'].xcom_pull(
            task_ids='bronze_layer.process_reddit_stories',
            key='etl_run_id'
        ) or f"silver_{execution_date}_{context.get('task_instance').try_number}"
        
        self.log.info(f"Starting silver layer processing")
        self.log.info(f"Batch size: {self.batch_size}, Quality threshold: {self.quality_threshold}")
        self.log.info(f"ETL Run ID: {etl_run_id}")
        
        # Run silver processing asynchronously
        result = asyncio.run(self._run_silver_processing(etl_run_id, target_date, bronze_result))
        
        self.log.info(f"Silver processing completed: {result}")
        
        # Store results in XCom for downstream tasks
        context['task_instance'].xcom_push(key='silver_result', value=result)
        context['task_instance'].xcom_push(key='etl_run_id', value=etl_run_id)
        
        return result
    
    async def _run_silver_processing(
        self,
        etl_run_id: str,
        target_date: str,
        bronze_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run the actual silver processing"""
        processor = SilverProcessor()
        
        try:
            # Initialize processor
            initialized = await processor.initialize()
            if not initialized:
                raise Exception("Failed to initialize silver processor")
            
            # Update processor configuration
            processor.min_quality_score = self.quality_threshold
            
            # Process batch
            batch_result = await processor.process_batch(
                batch_size=self.batch_size,
                etl_run_id=etl_run_id
            )
            
            # Get detailed statistics
            stats = processor.get_processing_stats()
            
            result = {
                'success': batch_result.get('error') is None,
                'stories_processed': stats['session_stats']['total_processed'],
                'chunks_generated': stats['session_stats']['total_chunks'],
                'total_cost': stats['cost_metrics']['total_cost'],
                'avg_quality_score': stats['quality_metrics']['avg_quality_score'],
                'language_breakdown': stats['language_breakdown'],
                'performance_metrics': stats['performance_metrics'],
                'skipped_low_quality': stats['session_stats']['skipped_low_quality'],
                'failed_stories': stats['session_stats']['failed_stories'],
                'etl_run_id': etl_run_id,
                'processing_date': target_date,
                'embedding_strategy': self.embedding_strategy
            }
            
            # Add error details if any
            if batch_result.get('error'):
                result['error_message'] = batch_result['error']
                result['success'] = False
            
            return result
            
        except Exception as e:
            self.log.error(f"Silver processing failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'etl_run_id': etl_run_id,
                'processing_date': target_date,
                'stories_processed': 0,
                'chunks_generated': 0,
                'total_cost': 0.0
            }
        finally:
            await processor.disconnect()
    
    def on_kill(self) -> None:
        """Handle task termination"""
        self.log.info("Silver processor operator killed")


class SilverQualityCheckOperator(BaseOperator):
    """
    Operator for silver layer quality validation
    """
    
    template_fields: Sequence[str] = ('target_date',)
    ui_color = '#E5E4E2'  # Light silver color
    
    @apply_defaults
    def __init__(
        self,
        quality_threshold: float = 0.95,
        target_date: Optional[str] = None,
        fail_on_quality_issues: bool = True,
        check_embedding_completeness: bool = True,
        check_language_consistency: bool = True,
        *args,
        **kwargs
    ):
        """
        Initialize Silver Quality Check Operator
        
        Args:
            quality_threshold: Minimum quality score required
            target_date: Date to validate (defaults to execution date)
            fail_on_quality_issues: Whether to fail task on quality issues
            check_embedding_completeness: Whether to validate embeddings
            check_language_consistency: Whether to validate language processing
        """
        super().__init__(*args, **kwargs)
        self.quality_threshold = quality_threshold
        self.target_date = target_date
        self.fail_on_quality_issues = fail_on_quality_issues
        self.check_embedding_completeness = check_embedding_completeness
        self.check_language_consistency = check_language_consistency
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute silver layer quality validation"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        # Get silver processing results from XCom if available
        silver_result = context['task_instance'].xcom_pull(
            task_ids='silver_layer.process_silver_chunks',
            key='silver_result'
        )
        
        self.log.info(f"Starting silver layer quality validation for {target_date}")
        self.log.info(f"Quality threshold: {self.quality_threshold}")
        
        # Run quality check
        result = asyncio.run(self._run_quality_check(target_date, silver_result))
        
        # Check if we should fail the task
        if self.fail_on_quality_issues and not result['success']:
            raise Exception(f"Silver layer quality check failed: {result.get('error_message')}")
        
        self.log.info(f"Silver quality check completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='silver_quality_result', value=result)
        
        return result
    
    async def _run_quality_check(
        self,
        target_date: str,
        silver_result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run the actual quality validation"""
        from etl.medallion.quality_manager import QualityManager
        
        quality_manager = QualityManager()
        
        try:
            # Initialize quality manager
            initialized = await quality_manager.initialize()
            if not initialized:
                raise Exception("Failed to initialize quality manager")
            
            # Run silver layer validation
            quality_report = await quality_manager.validate_silver_layer()
            
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
                'layer': 'silver'
            }
            
            # Add specific silver layer metrics
            if silver_result:
                result['processing_metrics'] = {
                    'stories_processed': silver_result.get('stories_processed', 0),
                    'chunks_generated': silver_result.get('chunks_generated', 0),
                    'total_cost': silver_result.get('total_cost', 0.0),
                    'language_breakdown': silver_result.get('language_breakdown', {}),
                    'skipped_low_quality': silver_result.get('skipped_low_quality', 0)
                }
            
            if not success:
                result['error_message'] = f"Quality score {quality_report.success_rate:.2f} below threshold {self.quality_threshold}"
                
                # Add details about failed checks
                failed_check_details = []
                for check in quality_report.check_results:
                    if not check.success:
                        failed_check_details.append({
                            'check_name': check.check_name,
                            'observed_value': check.observed_value,
                            'expected_value': check.expected_value,
                            'details': check.details
                        })
                result['failed_check_details'] = failed_check_details
                
                # Add specific silver layer recommendations
                recommendations = []
                if self.check_embedding_completeness:
                    recommendations.append("Check embedding generation process")
                if self.check_language_consistency:
                    recommendations.append("Validate language detection accuracy")
                result['recommendations'] = recommendations
            
            return result
            
        except Exception as e:
            self.log.error(f"Silver quality check failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'validation_date': target_date,
                'layer': 'silver'
            }
        finally:
            await quality_manager.disconnect()


class SilverCostAnalysisOperator(BaseOperator):
    """
    Operator for analyzing silver layer processing costs
    """
    
    template_fields: Sequence[str] = ('target_date',)
    ui_color = '#D3D3D3'  # Light gray silver
    
    @apply_defaults
    def __init__(
        self,
        cost_threshold: float = 50.0,
        target_date: Optional[str] = None,
        alert_on_high_costs: bool = True,
        *args,
        **kwargs
    ):
        """
        Initialize Silver Cost Analysis Operator
        
        Args:
            cost_threshold: Daily cost threshold for alerts
            target_date: Date to analyze (defaults to execution date)  
            alert_on_high_costs: Whether to alert on high costs
        """
        super().__init__(*args, **kwargs)
        self.cost_threshold = cost_threshold
        self.target_date = target_date
        self.alert_on_high_costs = alert_on_high_costs
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute silver layer cost analysis"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        # Get silver processing results from XCom
        silver_result = context['task_instance'].xcom_pull(
            task_ids='silver_layer.process_silver_chunks',
            key='silver_result'
        )
        
        self.log.info(f"Starting silver layer cost analysis for {target_date}")
        
        # Analyze costs
        result = self._analyze_costs(target_date, silver_result)
        
        # Check for cost alerts
        if self.alert_on_high_costs and result['total_cost'] > self.cost_threshold:
            self.log.warning(f"High cost alert: ${result['total_cost']:.2f} exceeds threshold ${self.cost_threshold}")
        
        self.log.info(f"Silver cost analysis completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='silver_cost_analysis', value=result)
        
        return result
    
    def _analyze_costs(self, target_date: str, silver_result: Optional[Dict] = None) -> Dict[str, Any]:
        """Analyze processing costs"""
        if not silver_result:
            return {
                'success': False,
                'error_message': 'No silver processing results available',
                'analysis_date': target_date
            }
        
        total_cost = silver_result.get('total_cost', 0.0)
        stories_processed = silver_result.get('stories_processed', 0)
        chunks_generated = silver_result.get('chunks_generated', 0)
        
        # Calculate cost metrics
        cost_per_story = total_cost / max(stories_processed, 1)
        cost_per_chunk = total_cost / max(chunks_generated, 1)
        
        # Cost breakdown analysis
        language_breakdown = silver_result.get('language_breakdown', {})
        
        result = {
            'success': True,
            'analysis_date': target_date,
            'total_cost': total_cost,
            'cost_threshold': self.cost_threshold,
            'cost_metrics': {
                'cost_per_story': cost_per_story,
                'cost_per_chunk': cost_per_chunk,
                'stories_processed': stories_processed,
                'chunks_generated': chunks_generated
            },
            'language_cost_breakdown': {
                'chinese_stories': language_breakdown.get('chinese', 0),
                'english_stories': language_breakdown.get('english', 0),
                'mixed_stories': language_breakdown.get('mixed', 0)
            },
            'cost_efficiency': {
                'within_budget': total_cost <= self.cost_threshold,
                'efficiency_rating': min(100, (self.cost_threshold / max(total_cost, 0.01)) * 100)
            },
            'recommendations': []
        }
        
        # Add cost optimization recommendations
        if total_cost > self.cost_threshold:
            result['recommendations'].append(f"Daily cost ${total_cost:.2f} exceeds budget ${self.cost_threshold}")
        
        if cost_per_story > 1.0:
            result['recommendations'].append("High cost per story - consider quality threshold optimization")
        
        if chunks_generated / max(stories_processed, 1) > 50:
            result['recommendations'].append("High chunk ratio - consider chunk size optimization")
        
        return result