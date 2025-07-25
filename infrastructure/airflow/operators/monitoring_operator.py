"""
Monitoring Operator
Custom Airflow operator for system monitoring and alerting
"""

from typing import Any, Dict, Optional, Sequence, List
from airflow.models import BaseOperator
from airflow.utils.context import Context
from airflow.utils.decorators import apply_defaults
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


class MonitoringOperator(BaseOperator):
    """
    Custom Airflow operator for monitoring system performance and costs
    
    Monitors various aspects of the medallion pipeline including:
    - Cost analysis and budget tracking
    - Performance metrics and bottlenecks
    - Error rates and system health
    - Resource utilization
    """
    
    template_fields: Sequence[str] = ('monitoring_type', 'target_date')
    template_ext: Sequence[str] = ()
    ui_color = '#87CEEB'  # Sky blue for monitoring
    
    @apply_defaults
    def __init__(
        self,
        monitoring_type: str,
        alert_threshold: Optional[Dict[str, Any]] = None,
        target_date: Optional[str] = None,
        send_alerts: bool = True,
        include_recommendations: bool = True,
        *args,
        **kwargs
    ):
        """
        Initialize Monitoring Operator
        
        Args:
            monitoring_type: Type of monitoring ('cost_analysis', 'performance_analysis', 'health_check')
            alert_threshold: Thresholds for triggering alerts
            target_date: Date to monitor (defaults to execution date)
            send_alerts: Whether to send alerts when thresholds exceeded
            include_recommendations: Whether to include optimization recommendations
        """
        super().__init__(*args, **kwargs)
        self.monitoring_type = monitoring_type
        self.alert_threshold = alert_threshold or {}
        self.target_date = target_date
        self.send_alerts = send_alerts
        self.include_recommendations = include_recommendations
        
        # Validate monitoring type
        valid_types = ['cost_analysis', 'performance_analysis', 'health_check', 'resource_utilization']
        if self.monitoring_type not in valid_types:
            raise ValueError(f"Invalid monitoring_type '{self.monitoring_type}'. Must be one of {valid_types}")
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute monitoring analysis"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting {self.monitoring_type} monitoring for {target_date}")
        self.log.info(f"Alert thresholds: {self.alert_threshold}")
        
        # Run monitoring based on type
        if self.monitoring_type == 'cost_analysis':
            result = self._run_cost_analysis(target_date, context)
        elif self.monitoring_type == 'performance_analysis':
            result = self._run_performance_analysis(target_date, context)
        elif self.monitoring_type == 'health_check':
            result = self._run_health_check(target_date, context)
        elif self.monitoring_type == 'resource_utilization':
            result = self._run_resource_utilization(target_date, context)
        else:
            raise ValueError(f"Unsupported monitoring type: {self.monitoring_type}")
        
        # Check for alerts
        alerts = self._check_alerts(result)
        result['alerts'] = alerts
        
        if alerts and self.send_alerts:
            self._send_monitoring_alerts(alerts, context)
        
        self.log.info(f"Monitoring analysis completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key=f'{self.monitoring_type}_result', value=result)
        
        return result
    
    def _run_cost_analysis(self, target_date: str, context: Context) -> Dict[str, Any]:
        """Run cost analysis monitoring"""
        # Get processing results from XCom
        bronze_result = context['task_instance'].xcom_pull(key='bronze_result')
        silver_result = context['task_instance'].xcom_pull(key='silver_result')
        gold_result = context['task_instance'].xcom_pull(key='gold_result')
        
        # Calculate costs
        total_cost = 0.0
        cost_breakdown = {}
        
        if silver_result:
            silver_cost = silver_result.get('total_cost', 0.0)
            total_cost += silver_cost
            cost_breakdown['silver_processing'] = silver_cost
            cost_breakdown['embedding_generation'] = silver_cost * 0.7  # Estimate
            cost_breakdown['model_processing'] = silver_cost * 0.3      # Estimate
        
        # Add infrastructure costs (mock data)
        infrastructure_cost = 5.50  # Daily infrastructure cost
        total_cost += infrastructure_cost
        cost_breakdown['infrastructure'] = infrastructure_cost
        
        # Calculate metrics
        stories_processed = (bronze_result or {}).get('stories_processed', 0) + \
                          (silver_result or {}).get('stories_processed', 0)
        
        cost_per_story = total_cost / max(stories_processed, 1)
        
        result = {
            'monitoring_type': 'cost_analysis',
            'analysis_date': target_date,
            'total_daily_cost': total_cost,
            'cost_breakdown': cost_breakdown,
            'cost_metrics': {
                'cost_per_story': cost_per_story,
                'stories_processed': stories_processed,
                'cost_efficiency_rating': min(100, (50 / max(total_cost, 0.01)) * 100)  # Target $50/day
            },
            'budget_analysis': {
                'daily_budget': 50.0,
                'budget_utilization_percentage': (total_cost / 50.0) * 100,
                'remaining_budget': max(0, 50.0 - total_cost),
                'projected_monthly_cost': total_cost * 30
            }
        }
        
        if self.include_recommendations:
            result['recommendations'] = self._get_cost_recommendations(result)
        
        return result
    
    def _run_performance_analysis(self, target_date: str, context: Context) -> Dict[str, Any]:
        """Run performance analysis monitoring"""
        # Get processing results from XCom
        bronze_result = context['task_instance'].xcom_pull(key='bronze_result')
        silver_result = context['task_instance'].xcom_pull(key='silver_result')
        gold_result = context['task_instance'].xcom_pull(key='gold_result')
        
        # Calculate performance metrics
        total_processing_time = 0
        processing_breakdown = {}
        
        if bronze_result:
            bronze_time = bronze_result.get('processing_time_ms', 0)
            total_processing_time += bronze_time
            processing_breakdown['bronze_layer'] = bronze_time
        
        if silver_result:
            silver_time = silver_result.get('performance_metrics', {}).get('avg_processing_time_ms', 0)
            total_processing_time += silver_time
            processing_breakdown['silver_layer'] = silver_time
        
        if gold_result:
            gold_time = gold_result.get('processing_time_ms', 0)
            total_processing_time += gold_time
            processing_breakdown['gold_layer'] = gold_time
        
        # Calculate throughput
        total_stories = (bronze_result or {}).get('stories_processed', 0)
        throughput = total_stories / max(total_processing_time / 1000 / 60, 1)  # stories per minute
        
        result = {
            'monitoring_type': 'performance_analysis',
            'analysis_date': target_date,
            'total_processing_time_ms': total_processing_time,
            'processing_breakdown_ms': processing_breakdown,
            'performance_metrics': {
                'throughput_stories_per_minute': throughput,
                'avg_processing_time_per_story_ms': total_processing_time / max(total_stories, 1),
                'total_stories_processed': total_stories,
                'pipeline_efficiency_rating': min(100, (600000 / max(total_processing_time, 1)) * 100)  # Target 10min total
            },
            'bottleneck_analysis': self._identify_performance_bottlenecks(processing_breakdown)
        }
        
        if self.include_recommendations:
            result['recommendations'] = self._get_performance_recommendations(result)
        
        return result
    
    def _run_health_check(self, target_date: str, context: Context) -> Dict[str, Any]:
        """Run system health check monitoring"""
        # Get quality results from XCom
        bronze_quality = context['task_instance'].xcom_pull(key='bronze_quality_result')
        silver_quality = context['task_instance'].xcom_pull(key='silver_quality_result')
        gold_quality = context['task_instance'].xcom_pull(key='gold_quality_result')
        
        # Calculate health metrics
        health_metrics = {
            'bronze_layer_health': self._calculate_layer_health(bronze_quality),
            'silver_layer_health': self._calculate_layer_health(silver_quality),
            'gold_layer_health': self._calculate_layer_health(gold_quality)
        }
        
        overall_health = sum(health_metrics.values()) / len(health_metrics)
        
        # Check system components
        component_status = {
            'database_connectivity': True,  # Would check actual DB connection
            'model_availability': True,     # Would check model APIs
            'embedding_service': True,      # Would check embedding service
            'data_sources': True            # Would check Reddit/PTT APIs
        }
        
        result = {
            'monitoring_type': 'health_check',
            'analysis_date': target_date,
            'overall_health_score': overall_health,
            'layer_health_scores': health_metrics,
            'component_status': component_status,
            'system_status': 'HEALTHY' if overall_health > 0.8 else 'DEGRADED' if overall_health > 0.6 else 'UNHEALTHY',
            'health_issues': self._identify_health_issues(health_metrics, component_status)
        }
        
        if self.include_recommendations:
            result['recommendations'] = self._get_health_recommendations(result)
        
        return result
    
    def _run_resource_utilization(self, target_date: str, context: Context) -> Dict[str, Any]:
        """Run resource utilization monitoring"""
        # Mock resource utilization data
        # In a real implementation, this would query actual system metrics
        
        result = {
            'monitoring_type': 'resource_utilization',
            'analysis_date': target_date,
            'compute_resources': {
                'cpu_utilization_percentage': 65.5,
                'memory_utilization_percentage': 72.3,
                'disk_utilization_percentage': 45.8,
                'network_io_mbps': 123.4
            },
            'database_resources': {
                'connection_pool_utilization': 68.0,
                'query_performance_avg_ms': 145,
                'storage_utilization_percentage': 52.1
            },
            'model_resources': {
                'api_rate_limit_utilization': 23.5,
                'model_response_time_avg_ms': 1850,
                'embedding_queue_size': 12
            },
            'resource_efficiency': {
                'overall_efficiency_score': 78.5,
                'cost_per_resource_unit': 0.045,
                'resource_waste_percentage': 15.2
            }
        }
        
        if self.include_recommendations:
            result['recommendations'] = self._get_resource_recommendations(result)
        
        return result
    
    def _check_alerts(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any metrics exceed alert thresholds"""
        alerts = []
        
        if self.monitoring_type == 'cost_analysis':
            daily_cost = result.get('total_daily_cost', 0)
            cost_threshold = self.alert_threshold.get('daily_cost', 50.0)
            
            if daily_cost > cost_threshold:
                alerts.append({
                    'type': 'COST_ALERT',
                    'severity': 'HIGH',
                    'message': f"Daily cost ${daily_cost:.2f} exceeds threshold ${cost_threshold}",
                    'metric': 'daily_cost',
                    'value': daily_cost,
                    'threshold': cost_threshold
                })
            
            cost_spike = self.alert_threshold.get('cost_spike_percentage', 20.0)
            budget_util = result.get('budget_analysis', {}).get('budget_utilization_percentage', 0)
            
            if budget_util > 90:
                alerts.append({
                    'type': 'BUDGET_ALERT',
                    'severity': 'CRITICAL',
                    'message': f"Budget utilization {budget_util:.1f}% critically high",
                    'metric': 'budget_utilization',
                    'value': budget_util,
                    'threshold': 90
                })
        
        elif self.monitoring_type == 'performance_analysis':
            avg_time = result.get('performance_metrics', {}).get('avg_processing_time_per_story_ms', 0)
            time_threshold = self.alert_threshold.get('avg_processing_time_ms', 30000)
            
            if avg_time > time_threshold:
                alerts.append({
                    'type': 'PERFORMANCE_ALERT',
                    'severity': 'MEDIUM',
                    'message': f"Average processing time {avg_time:.0f}ms exceeds threshold {time_threshold}ms",
                    'metric': 'avg_processing_time',
                    'value': avg_time,
                    'threshold': time_threshold
                })
        
        elif self.monitoring_type == 'health_check':
            health_score = result.get('overall_health_score', 1.0)
            health_threshold = self.alert_threshold.get('min_health_score', 0.8)
            
            if health_score < health_threshold:
                alerts.append({
                    'type': 'HEALTH_ALERT',
                    'severity': 'HIGH',
                    'message': f"System health score {health_score:.2f} below threshold {health_threshold}",
                    'metric': 'overall_health',
                    'value': health_score,
                    'threshold': health_threshold
                })
        
        return alerts
    
    def _send_monitoring_alerts(self, alerts: List[Dict[str, Any]], context: Context) -> None:
        """Send monitoring alerts"""
        for alert in alerts:
            self.log.warning(f"MONITORING ALERT: {alert}")
        
        # Store alerts in XCom for potential email operator pickup
        context['task_instance'].xcom_push(key='monitoring_alerts', value=alerts)
    
    def _calculate_layer_health(self, quality_result: Optional[Dict]) -> float:
        """Calculate health score for a layer based on quality results"""
        if not quality_result:
            return 0.5  # Unknown health
        
        if not quality_result.get('success', False):
            return 0.3  # Poor health
        
        quality_score = quality_result.get('quality_score', 0.0)
        return min(1.0, quality_score + 0.1)  # Slight bonus for passing
    
    def _identify_performance_bottlenecks(self, processing_breakdown: Dict[str, int]) -> Dict[str, Any]:
        """Identify performance bottlenecks"""
        if not processing_breakdown:
            return {'bottlenecks': [], 'recommendations': []}
        
        total_time = sum(processing_breakdown.values())
        bottlenecks = []
        
        for layer, time_ms in processing_breakdown.items():
            percentage = (time_ms / max(total_time, 1)) * 100
            if percentage > 50:  # Layer takes more than 50% of total time
                bottlenecks.append({
                    'layer': layer,
                    'time_ms': time_ms,
                    'percentage_of_total': percentage,
                    'severity': 'HIGH' if percentage > 70 else 'MEDIUM'
                })
        
        return {
            'bottlenecks': bottlenecks,
            'total_processing_time': total_time,
            'slowest_layer': max(processing_breakdown.items(), key=lambda x: x[1])[0] if processing_breakdown else None
        }
    
    def _identify_health_issues(self, health_metrics: Dict[str, float], component_status: Dict[str, bool]) -> List[str]:
        """Identify health issues"""
        issues = []
        
        for layer, health_score in health_metrics.items():
            if health_score < 0.7:
                issues.append(f"{layer} health score low: {health_score:.2f}")
        
        for component, status in component_status.items():
            if not status:
                issues.append(f"{component} component unavailable")
        
        return issues
    
    def _get_cost_recommendations(self, result: Dict[str, Any]) -> List[str]:
        """Get cost optimization recommendations"""
        recommendations = []
        
        total_cost = result.get('total_daily_cost', 0)
        budget = result.get('budget_analysis', {}).get('daily_budget', 50)
        
        if total_cost > budget:
            recommendations.append(f"Daily cost ${total_cost:.2f} exceeds budget ${budget} - implement cost optimization")
        
        cost_breakdown = result.get('cost_breakdown', {})
        embedding_cost = cost_breakdown.get('embedding_generation', 0)
        
        if embedding_cost > total_cost * 0.6:
            recommendations.append("Embedding costs high - consider using sentence transformers for non-critical embeddings")
        
        efficiency = result.get('cost_metrics', {}).get('cost_efficiency_rating', 0)
        if efficiency < 70:
            recommendations.append("Cost efficiency low - review batch sizes and model selection")
        
        return recommendations
    
    def _get_performance_recommendations(self, result: Dict[str, Any]) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        bottlenecks = result.get('bottleneck_analysis', {}).get('bottlenecks', [])
        for bottleneck in bottlenecks:
            layer = bottleneck['layer']
            recommendations.append(f"Optimize {layer} processing - identified as bottleneck")
        
        throughput = result.get('performance_metrics', {}).get('throughput_stories_per_minute', 0)
        if throughput < 5:  # Less than 5 stories per minute
            recommendations.append("Low throughput detected - consider increasing parallel processing")
        
        return recommendations
    
    def _get_health_recommendations(self, result: Dict[str, Any]) -> List[str]:
        """Get health improvement recommendations"""
        recommendations = []
        
        health_issues = result.get('health_issues', [])
        for issue in health_issues:
            if 'health score low' in issue:
                recommendations.append(f"Investigate and resolve: {issue}")
            elif 'unavailable' in issue:
                recommendations.append(f"Restore service: {issue}")
        
        overall_health = result.get('overall_health_score', 1.0)
        if overall_health < 0.8:
            recommendations.append("Overall system health degraded - review all pipeline components")
        
        return recommendations
    
    def _get_resource_recommendations(self, result: Dict[str, Any]) -> List[str]:
        """Get resource optimization recommendations"""
        recommendations = []
        
        compute = result.get('compute_resources', {})
        if compute.get('cpu_utilization_percentage', 0) > 80:
            recommendations.append("High CPU utilization - consider scaling compute resources")
        
        if compute.get('memory_utilization_percentage', 0) > 85:
            recommendations.append("High memory utilization - optimize memory usage or scale up")
        
        efficiency = result.get('resource_efficiency', {}).get('overall_efficiency_score', 0)
        if efficiency < 70:
            recommendations.append("Resource efficiency low - review resource allocation and usage patterns")
        
        return recommendations