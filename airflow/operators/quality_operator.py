"""
Quality Validation Operator
Custom Airflow operator for data quality validation across medallion layers
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

from etl.medallion.quality_manager import QualityManager


class QualityValidationOperator(BaseOperator):
    """
    Custom Airflow operator for data quality validation
    
    Validates data quality across bronze, silver, and gold layers using
    Great Expectations integration with configurable thresholds.
    """
    
    template_fields: Sequence[str] = ('layer', 'target_date')
    template_ext: Sequence[str] = ()
    ui_color = '#98FB98'  # Light green for quality
    
    @apply_defaults
    def __init__(
        self,
        layer: str,
        quality_threshold: float = 0.9,
        target_date: Optional[str] = None,
        fail_on_quality_issues: bool = True,
        alert_on_quality_issues: bool = True,
        table_name: Optional[str] = None,
        *args,
        **kwargs
    ):
        """
        Initialize Quality Validation Operator
        
        Args:
            layer: Medallion layer to validate ('bronze', 'silver', 'gold')
            quality_threshold: Minimum quality score required (0.0-1.0)
            target_date: Date to validate (defaults to execution date)
            fail_on_quality_issues: Whether to fail task on quality issues
            alert_on_quality_issues: Whether to send alerts on quality issues
            table_name: Specific table to validate (uses default if None)
        """
        super().__init__(*args, **kwargs)
        self.layer = layer.lower()
        self.quality_threshold = quality_threshold
        self.target_date = target_date
        self.fail_on_quality_issues = fail_on_quality_issues
        self.alert_on_quality_issues = alert_on_quality_issues
        self.table_name = table_name
        
        # Validate layer parameter
        if self.layer not in ['bronze', 'silver', 'gold']:
            raise ValueError(f"Invalid layer '{self.layer}'. Must be 'bronze', 'silver', or 'gold'")
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute quality validation"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting quality validation for {self.layer} layer")
        self.log.info(f"Quality threshold: {self.quality_threshold}")
        self.log.info(f"Target date: {target_date}")
        
        # Run quality validation asynchronously
        result = asyncio.run(self._run_quality_validation(target_date))
        
        # Handle quality issues
        if not result['success']:
            error_msg = f"{self.layer.title()} layer quality check failed: {result.get('error_message', 'Unknown error')}"
            
            if self.alert_on_quality_issues:
                self._send_quality_alert(result, context)
            
            if self.fail_on_quality_issues:
                raise Exception(error_msg)
            else:
                self.log.warning(error_msg)
        
        self.log.info(f"Quality validation completed: {result}")
        
        # Store results in XCom for downstream tasks
        context['task_instance'].xcom_push(key=f'{self.layer}_quality_result', value=result)
        
        return result
    
    async def _run_quality_validation(self, target_date: str) -> Dict[str, Any]:
        """Run the actual quality validation"""
        quality_manager = QualityManager()
        
        try:
            # Initialize quality manager
            initialized = await quality_manager.initialize()
            if not initialized:
                raise Exception("Failed to initialize quality manager")
            
            # Run validation based on layer
            if self.layer == 'bronze':
                table_name = self.table_name or "bronze_stories"
                quality_report = await quality_manager.validate_bronze_layer(table_name)
            elif self.layer == 'silver':
                table_name = self.table_name or "silver_story_chunks"
                quality_report = await quality_manager.validate_silver_layer(table_name)
            elif self.layer == 'gold':
                table_name = self.table_name or "gold_layer_metrics"
                quality_report = await quality_manager.validate_gold_layer(table_name)
            else:
                raise ValueError(f"Invalid layer: {self.layer}")
            
            # Evaluate results against threshold
            meets_threshold = quality_report.success_rate >= self.quality_threshold
            
            result = {
                'success': meets_threshold,
                'layer': self.layer,
                'table_name': table_name,
                'quality_score': quality_report.success_rate,
                'threshold': self.quality_threshold,
                'total_checks': quality_report.total_checks,
                'passed_checks': quality_report.passed_checks,
                'failed_checks': quality_report.failed_checks,
                'processing_time_ms': quality_report.processing_time_ms,
                'validation_date': target_date,
                'check_results': [
                    {
                        'check_name': check.check_name,
                        'success': check.success,
                        'expectation_type': check.expectation_type,
                        'observed_value': check.observed_value,
                        'expected_value': check.expected_value,
                        'details': check.details
                    }
                    for check in quality_report.check_results
                ],
                'metadata': quality_report.metadata
            }
            
            if not meets_threshold:
                result['error_message'] = (
                    f"Quality score {quality_report.success_rate:.3f} below threshold {self.quality_threshold}"
                )
                
                # Add failed check summaries
                failed_checks = [check for check in quality_report.check_results if not check.success]
                result['failed_check_summary'] = [
                    f"{check.check_name}: observed={check.observed_value}, expected={check.expected_value}"
                    for check in failed_checks
                ]
                
                # Add recommendations based on layer
                result['recommendations'] = self._get_quality_recommendations(failed_checks)
            
            return result
            
        except Exception as e:
            self.log.error(f"Quality validation failed: {str(e)}")
            return {
                'success': False,
                'layer': self.layer,
                'error_message': str(e),
                'validation_date': target_date,
                'quality_score': 0.0,
                'threshold': self.quality_threshold
            }
        finally:
            await quality_manager.disconnect()
    
    def _get_quality_recommendations(self, failed_checks) -> list:
        """Generate recommendations based on failed checks and layer"""
        recommendations = []
        
        if self.layer == 'bronze':
            if any('null' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Check data source connectivity and scraping processes")
            if any('duplicate' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Review duplicate detection logic in data ingestion")
            if any('content' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Validate content quality filters and scraping parameters")
                
        elif self.layer == 'silver':
            if any('embedding' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Check embedding generation process and API connectivity")
            if any('quality' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Review content quality assessment thresholds")
            if any('language' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Validate language detection and processing models")
                
        elif self.layer == 'gold':
            if any('freshness' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Check pipeline scheduling and data processing timing")
            if any('metric' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Validate business metric calculation logic")
            if any('business' in check.check_name.lower() for check in failed_checks):
                recommendations.append("Review business rule validation and KPI definitions")
        
        # General recommendations
        recommendations.append(f"Review {self.layer} layer data processing configuration")
        recommendations.append("Check for recent changes in data sources or processing logic")
        
        return recommendations
    
    def _send_quality_alert(self, result: Dict[str, Any], context: Context) -> None:
        """Send quality alert notification"""
        try:
            # In a real implementation, this would send alerts via email, Slack, etc.
            alert_data = {
                'layer': self.layer,
                'quality_score': result.get('quality_score', 0.0),
                'threshold': self.quality_threshold,
                'failed_checks': result.get('failed_checks', 0),
                'execution_date': context.get('ds'),
                'dag_id': context.get('dag').dag_id,
                'task_id': context.get('task').task_id
            }
            
            self.log.warning(f"QUALITY ALERT: {alert_data}")
            
            # Store alert in XCom for potential email operator pickup
            context['task_instance'].xcom_push(key='quality_alert', value=alert_data)
            
        except Exception as e:
            self.log.error(f"Failed to send quality alert: {e}")


class ComprehensiveQualityCheckOperator(BaseOperator):
    """
    Operator for comprehensive quality validation across all layers
    """
    
    template_fields: Sequence[str] = ('target_date',)
    ui_color = '#90EE90'  # Light green
    
    @apply_defaults
    def __init__(
        self,
        target_date: Optional[str] = None,
        quality_thresholds: Optional[Dict[str, float]] = None,
        fail_on_critical_issues: bool = True,
        generate_quality_report: bool = True,
        *args,
        **kwargs
    ):
        """
        Initialize Comprehensive Quality Check Operator
        
        Args:
            target_date: Date to validate (defaults to execution date)
            quality_thresholds: Custom thresholds per layer
            fail_on_critical_issues: Whether to fail on critical quality issues
            generate_quality_report: Whether to generate detailed report
        """
        super().__init__(*args, **kwargs)
        self.target_date = target_date
        self.quality_thresholds = quality_thresholds or {
            'bronze': 0.90,
            'silver': 0.95,
            'gold': 0.98
        }
        self.fail_on_critical_issues = fail_on_critical_issues
        self.generate_quality_report = generate_quality_report
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute comprehensive quality validation"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting comprehensive quality validation for {target_date}")
        
        # Run comprehensive validation
        result = asyncio.run(self._run_comprehensive_validation(target_date))
        
        # Check for critical issues
        critical_issues = self._identify_critical_issues(result)
        
        if critical_issues and self.fail_on_critical_issues:
            error_msg = f"Critical quality issues detected: {critical_issues}"
            self.log.error(error_msg)
            raise Exception(error_msg)
        
        # Generate quality report if requested
        if self.generate_quality_report:
            report = self._generate_quality_report(result, target_date)
            context['task_instance'].xcom_push(key='quality_report', value=report)
        
        self.log.info(f"Comprehensive quality validation completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='comprehensive_quality_result', value=result)
        
        return result
    
    async def _run_comprehensive_validation(self, target_date: str) -> Dict[str, Any]:
        """Run comprehensive validation across all layers"""
        quality_manager = QualityManager()
        
        try:
            # Initialize quality manager
            initialized = await quality_manager.initialize()
            if not initialized:
                raise Exception("Failed to initialize quality manager")
            
            # Validate all layers
            all_results = await quality_manager.validate_all_layers()
            
            # Calculate overall metrics
            total_checks = sum(report.total_checks for report in all_results.values())
            total_passed = sum(report.passed_checks for report in all_results.values())
            overall_success_rate = total_passed / max(total_checks, 1)
            
            # Evaluate each layer against thresholds
            layer_results = {}
            overall_success = True
            
            for layer, report in all_results.items():
                threshold = self.quality_thresholds.get(layer, 0.9)
                meets_threshold = report.success_rate >= threshold
                overall_success = overall_success and meets_threshold
                
                layer_results[layer] = {
                    'success': meets_threshold,
                    'quality_score': report.success_rate,
                    'threshold': threshold,
                    'total_checks': report.total_checks,
                    'passed_checks': report.passed_checks,
                    'failed_checks': report.failed_checks,
                    'processing_time_ms': report.processing_time_ms
                }
            
            result = {
                'success': overall_success,
                'overall_quality_score': overall_success_rate,
                'validation_date': target_date,
                'layer_results': layer_results,
                'summary': {
                    'total_checks': total_checks,
                    'total_passed': total_passed,
                    'total_failed': total_checks - total_passed,
                    'layers_validated': len(all_results),
                    'layers_passed': sum(1 for r in layer_results.values() if r['success'])
                }
            }
            
            return result
            
        except Exception as e:
            self.log.error(f"Comprehensive quality validation failed: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'validation_date': target_date,
                'overall_quality_score': 0.0
            }
        finally:
            await quality_manager.disconnect()
    
    def _identify_critical_issues(self, result: Dict[str, Any]) -> list:
        """Identify critical quality issues"""
        critical_issues = []
        
        if not result.get('success', False):
            overall_score = result.get('overall_quality_score', 0.0)
            if overall_score < 0.8:
                critical_issues.append(f"Overall quality score critically low: {overall_score:.2f}")
        
        layer_results = result.get('layer_results', {})
        for layer, layer_result in layer_results.items():
            if not layer_result.get('success', False):
                score = layer_result.get('quality_score', 0.0)
                threshold = layer_result.get('threshold', 0.9)
                if score < threshold * 0.8:  # Critical if below 80% of threshold
                    critical_issues.append(f"{layer} layer critically below threshold: {score:.2f} < {threshold}")
        
        return critical_issues
    
    def _generate_quality_report(self, result: Dict[str, Any], target_date: str) -> Dict[str, Any]:
        """Generate detailed quality report"""
        report = {
            'report_date': target_date,
            'overall_status': 'PASS' if result.get('success', False) else 'FAIL',
            'overall_quality_score': result.get('overall_quality_score', 0.0),
            'executive_summary': {
                'total_layers_validated': len(result.get('layer_results', {})),
                'layers_passed': result.get('summary', {}).get('layers_passed', 0),
                'total_checks_performed': result.get('summary', {}).get('total_checks', 0),
                'checks_passed': result.get('summary', {}).get('total_passed', 0)
            },
            'layer_details': result.get('layer_results', {}),
            'recommendations': [],
            'action_items': []
        }
        
        # Add recommendations based on results
        if not result.get('success', False):
            report['recommendations'].extend([
                "Review data processing pipeline for quality issues",
                "Check data source connectivity and reliability",
                "Validate quality thresholds and expectations"
            ])
        
        # Add layer-specific action items
        for layer, layer_result in result.get('layer_results', {}).items():
            if not layer_result.get('success', False):
                report['action_items'].append(f"Investigate {layer} layer quality issues")
        
        return report