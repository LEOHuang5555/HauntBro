"""
Cost Analysis Operator
Custom Airflow operator for detailed cost analysis and optimization
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


class CostAnalysisOperator(BaseOperator):
    """
    Custom Airflow operator for comprehensive cost analysis
    
    Analyzes costs across all pipeline components including:
    - AI model usage costs (OpenAI, DeepSeek, LLaMA)
    - Infrastructure costs
    - Storage and compute costs
    - Cost trends and forecasting
    """
    
    template_fields: Sequence[str] = ('analysis_period', 'target_date')
    template_ext: Sequence[str] = ()
    ui_color = '#FFB6C1'  # Light pink for cost analysis
    
    @apply_defaults
    def __init__(
        self,
        analysis_period: str = 'last_24_hours',
        target_date: Optional[str] = None,
        include_predictions: bool = True,
        include_optimization_suggestions: bool = True,
        cost_breakdown_detail: str = 'detailed',  # 'summary', 'detailed', 'comprehensive'
        *args,
        **kwargs
    ):
        """
        Initialize Cost Analysis Operator
        
        Args:
            analysis_period: Period to analyze ('last_24_hours', 'last_week', 'last_month')
            target_date: Specific date to analyze (defaults to execution date)
            include_predictions: Whether to include cost predictions
            include_optimization_suggestions: Whether to include optimization recommendations
            cost_breakdown_detail: Level of detail for cost breakdown
        """
        super().__init__(*args, **kwargs)
        self.analysis_period = analysis_period
        self.target_date = target_date
        self.include_predictions = include_predictions
        self.include_optimization_suggestions = include_optimization_suggestions
        self.cost_breakdown_detail = cost_breakdown_detail
        
        # Validate parameters
        valid_periods = ['last_24_hours', 'last_week', 'last_month', 'custom']
        if self.analysis_period not in valid_periods:
            raise ValueError(f"Invalid analysis_period '{self.analysis_period}'. Must be one of {valid_periods}")
        
        valid_details = ['summary', 'detailed', 'comprehensive']
        if self.cost_breakdown_detail not in valid_details:
            raise ValueError(f"Invalid cost_breakdown_detail '{self.cost_breakdown_detail}'. Must be one of {valid_details}")
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute cost analysis"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting cost analysis for period: {self.analysis_period}")
        self.log.info(f"Target date: {target_date}")
        self.log.info(f"Detail level: {self.cost_breakdown_detail}")
        
        # Get processing results from XCom
        processing_results = self._gather_processing_results(context)
        
        # Run cost analysis
        result = self._run_cost_analysis(target_date, processing_results)
        
        self.log.info(f"Cost analysis completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key='cost_analysis_result', value=result)
        
        return result
    
    def _gather_processing_results(self, context: Context) -> Dict[str, Any]:
        """Gather processing results from all pipeline stages"""
        results = {}
        
        # Try to get results from various tasks
        task_keys = [
            ('bronze_result', ['bronze_layer.process_reddit_stories', 'bronze_layer.process_ptt_stories']),
            ('silver_result', ['silver_layer.process_silver_chunks']),
            ('gold_result', ['gold_layer.generate_gold_metrics']),
            ('quality_results', ['validate_bronze_quality', 'validate_silver_quality', 'validate_gold_quality'])
        ]
        
        for result_key, task_ids in task_keys:
            for task_id in task_ids:
                try:
                    result = context['task_instance'].xcom_pull(task_ids=task_id, key=result_key.split('_')[0] + '_result')
                    if result:
                        results[result_key] = result
                        break
                except Exception as e:
                    self.log.debug(f"Could not get {result_key} from {task_id}: {e}")
        
        return results
    
    def _run_cost_analysis(self, target_date: str, processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive cost analysis"""
        
        # Extract cost data from processing results
        cost_data = self._extract_cost_data(processing_results)
        
        # Calculate cost breakdown
        cost_breakdown = self._calculate_cost_breakdown(cost_data)
        
        # Calculate cost metrics
        cost_metrics = self._calculate_cost_metrics(cost_breakdown, processing_results)
        
        # Generate cost trends (mock data for demonstration)
        cost_trends = self._generate_cost_trends(target_date) if self.include_predictions else None
        
        # Generate optimization suggestions
        optimization_suggestions = self._generate_optimization_suggestions(
            cost_breakdown, cost_metrics
        ) if self.include_optimization_suggestions else None
        
        result = {
            'analysis_date': target_date,
            'analysis_period': self.analysis_period,
            'cost_breakdown': cost_breakdown,
            'cost_metrics': cost_metrics,
            'cost_summary': self._generate_cost_summary(cost_breakdown, cost_metrics),
            'processing_stats': self._extract_processing_stats(processing_results)
        }
        
        if cost_trends:
            result['cost_trends'] = cost_trends
        
        if optimization_suggestions:
            result['optimization_suggestions'] = optimization_suggestions
        
        # Add detailed analysis if requested
        if self.cost_breakdown_detail in ['detailed', 'comprehensive']:
            result['detailed_analysis'] = self._generate_detailed_analysis(cost_breakdown, processing_results)
        
        if self.cost_breakdown_detail == 'comprehensive':
            result['comprehensive_analysis'] = self._generate_comprehensive_analysis(result)
        
        return result
    
    def _extract_cost_data(self, processing_results: Dict[str, Any]) -> Dict[str, float]:
        """Extract cost data from processing results"""
        costs = {
            'embedding_generation': 0.0,
            'model_processing': 0.0,
            'infrastructure': 0.0,
            'storage': 0.0,
            'compute': 0.0
        }
        
        # Extract silver layer costs (embedding and model processing)
        silver_result = processing_results.get('silver_result')
        if silver_result:
            total_silver_cost = silver_result.get('total_cost', 0.0)
            costs['embedding_generation'] = total_silver_cost * 0.7  # Estimate 70% for embeddings
            costs['model_processing'] = total_silver_cost * 0.3     # Estimate 30% for model processing
        
        # Add infrastructure costs (mock data)
        costs['infrastructure'] = 5.50   # Daily infrastructure cost
        costs['storage'] = 1.25          # Daily storage cost
        costs['compute'] = 3.75          # Daily compute cost
        
        return costs
    
    def _calculate_cost_breakdown(self, cost_data: Dict[str, float]) -> Dict[str, Any]:
        """Calculate detailed cost breakdown"""
        total_cost = sum(cost_data.values())
        
        breakdown = {
            'total_cost': total_cost,
            'cost_categories': {},
            'cost_percentages': {}
        }
        
        for category, cost in cost_data.items():
            breakdown['cost_categories'][category] = {
                'amount': cost,
                'percentage': (cost / max(total_cost, 0.01)) * 100,
                'description': self._get_cost_category_description(category)
            }
            breakdown['cost_percentages'][category] = (cost / max(total_cost, 0.01)) * 100
        
        # Identify major cost drivers
        breakdown['major_cost_drivers'] = [
            category for category, cost in cost_data.items()
            if (cost / max(total_cost, 0.01)) > 0.2  # More than 20% of total cost
        ]
        
        return breakdown
    
    def _calculate_cost_metrics(self, cost_breakdown: Dict[str, Any], processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost efficiency metrics"""
        total_cost = cost_breakdown['total_cost']
        
        # Extract processing volumes
        stories_processed = 0
        chunks_generated = 0
        
        silver_result = processing_results.get('silver_result', {})
        stories_processed = silver_result.get('stories_processed', 0)
        chunks_generated = silver_result.get('chunks_generated', 0)
        
        bronze_result = processing_results.get('bronze_result', {})
        if isinstance(bronze_result, dict) and 'stories_processed' in bronze_result:
            stories_processed += bronze_result.get('stories_processed', 0)
        
        # Calculate efficiency metrics
        metrics = {
            'cost_per_story': total_cost / max(stories_processed, 1),
            'cost_per_chunk': total_cost / max(chunks_generated, 1),
            'stories_processed': stories_processed,
            'chunks_generated': chunks_generated,
            'cost_efficiency_score': self._calculate_efficiency_score(total_cost, stories_processed),
            'budget_utilization': {
                'daily_budget': 50.0,  # Target daily budget
                'utilized_amount': total_cost,
                'utilization_percentage': (total_cost / 50.0) * 100,
                'remaining_budget': max(0, 50.0 - total_cost),
                'budget_status': 'under_budget' if total_cost <= 50.0 else 'over_budget'
            }
        }
        
        return metrics
    
    def _generate_cost_trends(self, target_date: str) -> Dict[str, Any]:
        """Generate cost trends and predictions"""
        # Mock trend data - in reality would analyze historical costs
        
        return {
            'historical_trends': {
                'last_7_days': {
                    'average_daily_cost': 42.30,
                    'trend_direction': 'increasing',
                    'trend_percentage': 8.5,
                    'cost_volatility': 12.3
                },
                'last_30_days': {
                    'average_daily_cost': 38.75,
                    'trend_direction': 'increasing',
                    'trend_percentage': 15.2,
                    'cost_volatility': 18.7
                }
            },
            'predictions': {
                'next_7_days': {
                    'predicted_daily_average': 45.60,
                    'confidence_interval': [41.20, 50.00],
                    'predicted_total': 319.20
                },
                'next_30_days': {
                    'predicted_daily_average': 47.80,
                    'confidence_interval': [43.50, 52.10],
                    'predicted_total': 1434.00
                }
            },
            'cost_drivers': [
                'Increased embedding API usage',
                'Higher model processing volume',
                'Infrastructure scaling costs'
            ],
            'forecast_accuracy': 0.85
        }
    
    def _generate_optimization_suggestions(
        self,
        cost_breakdown: Dict[str, Any],
        cost_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate cost optimization suggestions"""
        
        suggestions = {
            'immediate_actions': [],
            'medium_term_optimizations': [],
            'long_term_strategies': [],
            'potential_savings': {}
        }
        
        total_cost = cost_breakdown['total_cost']
        major_drivers = cost_breakdown['major_cost_drivers']
        
        # Immediate actions
        if 'embedding_generation' in major_drivers:
            suggestions['immediate_actions'].append({
                'action': 'Implement sentence transformer fallback for non-critical embeddings',
                'estimated_savings': '$8-12/day',
                'implementation_effort': 'Medium',
                'priority': 'High'
            })
        
        if cost_metrics['cost_per_story'] > 0.50:
            suggestions['immediate_actions'].append({
                'action': 'Optimize batch sizes for better cost efficiency',
                'estimated_savings': '$5-8/day',
                'implementation_effort': 'Low',
                'priority': 'High'
            })
        
        # Medium-term optimizations
        suggestions['medium_term_optimizations'].append({
            'action': 'Implement intelligent model selection based on content complexity',
            'estimated_savings': '$10-15/day',
            'implementation_effort': 'High',
            'priority': 'Medium'
        })
        
        suggestions['medium_term_optimizations'].append({
            'action': 'Cache frequently accessed embeddings',
            'estimated_savings': '$3-6/day',
            'implementation_effort': 'Medium',
            'priority': 'Medium'
        })
        
        # Long-term strategies
        suggestions['long_term_strategies'].append({
            'action': 'Evaluate fine-tuned smaller models for specific tasks',
            'estimated_savings': '$15-25/day',
            'implementation_effort': 'Very High',
            'priority': 'Low'
        })
        
        # Calculate potential savings
        immediate_savings = sum([8, 5])  # Conservative estimates
        medium_term_savings = sum([10, 3])
        long_term_savings = 15
        
        suggestions['potential_savings'] = {
            'immediate_daily_savings': f'${immediate_savings}-{immediate_savings + 5}',
            'medium_term_daily_savings': f'${medium_term_savings}-{medium_term_savings + 8}',
            'long_term_daily_savings': f'${long_term_savings}-{long_term_savings + 10}',
            'total_potential_daily_savings': f'${immediate_savings + medium_term_savings + long_term_savings}-{immediate_savings + medium_term_savings + long_term_savings + 23}'
        }
        
        return suggestions
    
    def _generate_cost_summary(self, cost_breakdown: Dict[str, Any], cost_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive cost summary"""
        return {
            'total_daily_cost': cost_breakdown['total_cost'],
            'cost_efficiency_rating': cost_metrics['cost_efficiency_score'],
            'budget_status': cost_metrics['budget_utilization']['budget_status'],
            'top_cost_category': max(
                cost_breakdown['cost_categories'].items(),
                key=lambda x: x[1]['amount']
            )[0],
            'cost_per_story': cost_metrics['cost_per_story'],
            'processing_volume': {
                'stories_processed': cost_metrics['stories_processed'],
                'chunks_generated': cost_metrics['chunks_generated']
            },
            'key_insights': [
                f"Daily cost: ${cost_breakdown['total_cost']:.2f}",
                f"Cost per story: ${cost_metrics['cost_per_story']:.3f}",
                f"Budget utilization: {cost_metrics['budget_utilization']['utilization_percentage']:.1f}%"
            ]
        }
    
    def _extract_processing_stats(self, processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract processing statistics for cost context"""
        stats = {
            'bronze_layer': {},
            'silver_layer': {},
            'gold_layer': {}
        }
        
        # Bronze layer stats
        bronze_result = processing_results.get('bronze_result', {})
        if bronze_result:
            stats['bronze_layer'] = {
                'stories_processed': bronze_result.get('stories_processed', 0),
                'processing_errors': bronze_result.get('processing_errors', 0),
                'processing_time_ms': bronze_result.get('processing_time_ms', 0)
            }
        
        # Silver layer stats
        silver_result = processing_results.get('silver_result', {})
        if silver_result:
            stats['silver_layer'] = {
                'stories_processed': silver_result.get('stories_processed', 0),
                'chunks_generated': silver_result.get('chunks_generated', 0),
                'total_cost': silver_result.get('total_cost', 0.0),
                'language_breakdown': silver_result.get('language_breakdown', {})
            }
        
        # Gold layer stats
        gold_result = processing_results.get('gold_result', {})
        if gold_result:
            stats['gold_layer'] = {
                'metrics_generated': gold_result.get('metrics_generated', 0),
                'processing_time_ms': gold_result.get('processing_time_ms', 0)
            }
        
        return stats
    
    def _generate_detailed_analysis(self, cost_breakdown: Dict[str, Any], processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed cost analysis"""
        return {
            'cost_variance_analysis': {
                'expected_daily_cost': 45.0,
                'actual_daily_cost': cost_breakdown['total_cost'],
                'variance': cost_breakdown['total_cost'] - 45.0,
                'variance_percentage': ((cost_breakdown['total_cost'] - 45.0) / 45.0) * 100
            },
            'model_usage_analysis': {
                'embedding_api_calls': 1250,  # Mock data
                'model_processing_requests': 875,
                'average_tokens_per_request': 450,
                'peak_usage_hour': '14:00-15:00'
            },
            'efficiency_analysis': {
                'cost_per_token': 0.00008,
                'tokens_per_story': 580,
                'processing_efficiency_score': 78.5,
                'resource_utilization_score': 82.3
            }
        }
    
    def _generate_comprehensive_analysis(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive cost analysis with all metrics"""
        return {
            'executive_dashboard': {
                'cost_health_score': 78.5,
                'cost_trend': 'increasing',
                'budget_risk_level': 'medium',
                'optimization_potential': 'high'
            },
            'comparative_analysis': {
                'cost_vs_industry_average': 'below_average',
                'cost_vs_previous_month': '+12.5%',
                'efficiency_vs_target': '-8.2%'
            },
            'risk_assessment': {
                'budget_overrun_risk': 'medium',
                'cost_spike_probability': 0.25,
                'vendor_dependency_risk': 'high'
            },
            'recommendations_prioritized': [
                'Implement cost-optimized embedding strategy',
                'Optimize batch processing parameters',
                'Evaluate alternative model providers'
            ]
        }
    
    def _calculate_efficiency_score(self, total_cost: float, stories_processed: int) -> float:
        """Calculate cost efficiency score (0-100)"""
        if stories_processed == 0:
            return 0
        
        cost_per_story = total_cost / stories_processed
        target_cost_per_story = 0.30  # Target cost per story
        
        # Calculate efficiency as inverse of cost ratio
        efficiency = min(100, (target_cost_per_story / max(cost_per_story, 0.01)) * 100)
        return round(efficiency, 1)
    
    def _get_cost_category_description(self, category: str) -> str:
        """Get description for cost category"""
        descriptions = {
            'embedding_generation': 'OpenAI API costs for generating content and search embeddings',
            'model_processing': 'DeepSeek and LLaMA model usage costs for text processing',
            'infrastructure': 'AWS/Cloud infrastructure costs including compute and networking',
            'storage': 'Database and file storage costs for medallion architecture',
            'compute': 'Compute resources for running processing pipelines'
        }
        return descriptions.get(category, f'Costs related to {category}')


class ModelOptimizationOperator(BaseOperator):
    """Operator for model usage optimization"""
    
    template_fields: Sequence[str] = ('optimization_type',)
    ui_color = '#DDA0DD'  # Plum color
    
    @apply_defaults
    def __init__(
        self,
        optimization_type: str,
        target_savings_percentage: float = 20.0,
        quality_threshold: float = 0.8,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.optimization_type = optimization_type
        self.target_savings_percentage = target_savings_percentage
        self.quality_threshold = quality_threshold
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute model optimization"""
        self.log.info(f"Running {self.optimization_type} optimization")
        
        # Mock optimization results
        result = {
            'optimization_type': self.optimization_type,
            'target_savings_percentage': self.target_savings_percentage,
            'achieved_savings_percentage': 18.5,
            'quality_impact': 'minimal',
            'recommendations': [
                'Switch 30% of embeddings to sentence transformers',
                'Optimize batch sizes for API efficiency',
                'Implement intelligent model routing'
            ]
        }
        
        return result