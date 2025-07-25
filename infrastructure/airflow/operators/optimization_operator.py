"""
Optimization Operator
Custom Airflow operator for system optimization and performance tuning
"""

from typing import Any, Dict, Optional, Sequence, List
from airflow.models import BaseOperator
from airflow.utils.context import Context
from airflow.utils.decorators import apply_defaults
import json
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent.parent))


class ModelOptimizationOperator(BaseOperator):
    """
    Custom Airflow operator for model usage optimization
    
    Optimizes model selection, batch sizes, and processing parameters
    to achieve better cost efficiency while maintaining quality.
    """
    
    template_fields: Sequence[str] = ('optimization_type', 'target_date')
    template_ext: Sequence[str] = ()
    ui_color = '#DDA0DD'  # Plum color for optimization
    
    @apply_defaults
    def __init__(
        self,
        optimization_type: str,
        target_savings_percentage: float = 20.0,
        quality_threshold: float = 0.8,
        target_date: Optional[str] = None,
        dry_run: bool = True,
        *args,
        **kwargs
    ):
        """
        Initialize Model Optimization Operator
        
        Args:
            optimization_type: Type of optimization ('embedding_cost', 'model_efficiency', 'batch_optimization')
            target_savings_percentage: Target cost savings percentage
            quality_threshold: Minimum quality threshold to maintain
            target_date: Date to optimize for (defaults to execution date)
            dry_run: Whether to run in simulation mode
        """
        super().__init__(*args, **kwargs)
        self.optimization_type = optimization_type
        self.target_savings_percentage = target_savings_percentage
        self.quality_threshold = quality_threshold
        self.target_date = target_date
        self.dry_run = dry_run
        
        # Validate optimization type
        valid_types = ['embedding_cost', 'model_efficiency', 'batch_optimization', 'quality_cost_balance']
        if self.optimization_type not in valid_types:
            raise ValueError(f"Invalid optimization_type '{self.optimization_type}'. Must be one of {valid_types}")
    
    def execute(self, context: Context) -> Dict[str, Any]:
        """Execute model optimization"""
        execution_date = context.get('ds')
        target_date = self.target_date or execution_date
        
        self.log.info(f"Starting {self.optimization_type} optimization for {target_date}")
        self.log.info(f"Target savings: {self.target_savings_percentage}%")
        self.log.info(f"Quality threshold: {self.quality_threshold}")
        self.log.info(f"Dry run mode: {self.dry_run}")
        
        # Get current processing results for baseline
        baseline_data = self._gather_baseline_data(context)
        
        # Run optimization based on type
        if self.optimization_type == 'embedding_cost':
            result = self._optimize_embedding_costs(baseline_data, target_date)
        elif self.optimization_type == 'model_efficiency':
            result = self._optimize_model_efficiency(baseline_data, target_date)
        elif self.optimization_type == 'batch_optimization':
            result = self._optimize_batch_processing(baseline_data, target_date)
        elif self.optimization_type == 'quality_cost_balance':
            result = self._optimize_quality_cost_balance(baseline_data, target_date)
        else:
            raise ValueError(f"Unsupported optimization type: {self.optimization_type}")
        
        self.log.info(f"Optimization completed: {result}")
        
        # Store results in XCom
        context['task_instance'].xcom_push(key=f'{self.optimization_type}_optimization_result', value=result)
        
        return result
    
    def _gather_baseline_data(self, context: Context) -> Dict[str, Any]:
        """Gather baseline performance and cost data"""
        baseline = {
            'cost_data': {},
            'performance_data': {},
            'quality_data': {}
        }
        
        # Get cost analysis results
        try:
            cost_result = context['task_instance'].xcom_pull(key='cost_analysis_result')
            if cost_result:
                baseline['cost_data'] = {
                    'total_daily_cost': cost_result.get('cost_breakdown', {}).get('total_cost', 0),
                    'embedding_cost': cost_result.get('cost_breakdown', {}).get('cost_categories', {}).get('embedding_generation', {}).get('amount', 0),
                    'model_processing_cost': cost_result.get('cost_breakdown', {}).get('cost_categories', {}).get('model_processing', {}).get('amount', 0),
                    'cost_per_story': cost_result.get('cost_metrics', {}).get('cost_per_story', 0)
                }
        except Exception as e:
            self.log.warning(f"Could not get cost data: {e}")
        
        # Get performance data
        try:
            silver_result = context['task_instance'].xcom_pull(key='silver_result')
            if silver_result:
                baseline['performance_data'] = {
                    'stories_processed': silver_result.get('stories_processed', 0),
                    'chunks_generated': silver_result.get('chunks_generated', 0),
                    'avg_processing_time': silver_result.get('performance_metrics', {}).get('avg_processing_time_ms', 0),
                    'language_breakdown': silver_result.get('language_breakdown', {})
                }
        except Exception as e:
            self.log.warning(f"Could not get performance data: {e}")
        
        # Get quality data
        try:
            quality_result = context['task_instance'].xcom_pull(key='silver_quality_result')
            if quality_result:
                baseline['quality_data'] = {
                    'quality_score': quality_result.get('quality_score', 0),
                    'total_checks': quality_result.get('total_checks', 0),
                    'passed_checks': quality_result.get('passed_checks', 0)
                }
        except Exception as e:
            self.log.warning(f"Could not get quality data: {e}")
        
        return baseline
    
    def _optimize_embedding_costs(self, baseline_data: Dict[str, Any], target_date: str) -> Dict[str, Any]:
        """Optimize embedding generation costs"""
        current_embedding_cost = baseline_data.get('cost_data', {}).get('embedding_cost', 0)
        current_total_cost = baseline_data.get('cost_data', {}).get('total_daily_cost', 0)
        
        # Analysis of current embedding strategy
        optimization_strategies = [
            {
                'strategy': 'sentence_transformer_fallback',
                'description': 'Use sentence transformers for 40% of embeddings',
                'estimated_savings_percentage': 28.0,
                'quality_impact': 0.95,  # 95% quality retention
                'implementation_complexity': 'medium'
            },
            {
                'strategy': 'embedding_caching',
                'description': 'Cache embeddings for similar content',
                'estimated_savings_percentage': 15.0,
                'quality_impact': 1.0,  # No quality impact
                'implementation_complexity': 'low'
            },
            {
                'strategy': 'smart_batch_sizing',
                'description': 'Optimize batch sizes for embedding API',
                'estimated_savings_percentage': 12.0,
                'quality_impact': 1.0,  # No quality impact
                'implementation_complexity': 'low'
            },
            {
                'strategy': 'content_deduplication',
                'description': 'Skip embeddings for duplicate content',
                'estimated_savings_percentage': 8.0,
                'quality_impact': 1.0,  # No quality impact
                'implementation_complexity': 'medium'
            }
        ]
        
        # Filter strategies that meet quality threshold
        viable_strategies = [
            strategy for strategy in optimization_strategies
            if strategy['quality_impact'] >= self.quality_threshold
        ]
        
        # Calculate potential savings
        total_potential_savings = 0
        recommended_strategies = []
        
        for strategy in viable_strategies:
            if total_potential_savings < self.target_savings_percentage:
                recommended_strategies.append(strategy)
                total_potential_savings += strategy['estimated_savings_percentage']
        
        # Calculate new costs
        actual_savings_percentage = min(total_potential_savings, self.target_savings_percentage)
        estimated_new_embedding_cost = current_embedding_cost * (1 - actual_savings_percentage / 100)
        estimated_new_total_cost = current_total_cost - (current_embedding_cost - estimated_new_embedding_cost)
        
        result = {
            'optimization_type': 'embedding_cost',
            'optimization_date': target_date,
            'dry_run': self.dry_run,
            'baseline_metrics': {
                'current_embedding_cost': current_embedding_cost,
                'current_total_cost': current_total_cost,
                'current_cost_percentage': (current_embedding_cost / max(current_total_cost, 0.01)) * 100
            },
            'optimization_analysis': {
                'target_savings_percentage': self.target_savings_percentage,
                'achievable_savings_percentage': actual_savings_percentage,
                'estimated_new_embedding_cost': estimated_new_embedding_cost,
                'estimated_new_total_cost': estimated_new_total_cost,
                'estimated_daily_savings': current_embedding_cost - estimated_new_embedding_cost
            },
            'recommended_strategies': recommended_strategies,
            'implementation_plan': self._create_implementation_plan(recommended_strategies),
            'quality_assessment': {
                'quality_threshold': self.quality_threshold,
                'estimated_quality_retention': min([s['quality_impact'] for s in recommended_strategies]) if recommended_strategies else 1.0,
                'quality_risk_level': 'low' if min([s['quality_impact'] for s in recommended_strategies]) >= 0.9 else 'medium'
            }
        }
        
        return result
    
    def _optimize_model_efficiency(self, baseline_data: Dict[str, Any], target_date: str) -> Dict[str, Any]:
        """Optimize model selection and usage efficiency"""
        current_processing_cost = baseline_data.get('cost_data', {}).get('model_processing_cost', 0)
        current_processing_time = baseline_data.get('performance_data', {}).get('avg_processing_time', 0)
        language_breakdown = baseline_data.get('performance_data', {}).get('language_breakdown', {})
        
        optimization_strategies = [
            {
                'strategy': 'language_specific_routing',
                'description': 'Route content to optimal models based on language',
                'estimated_cost_reduction': 22.0,
                'estimated_speed_improvement': 18.0,
                'quality_impact': 1.05,  # Slight quality improvement
                'implementation_complexity': 'medium'
            },
            {
                'strategy': 'content_complexity_routing',
                'description': 'Use smaller models for simple content',
                'estimated_cost_reduction': 15.0,
                'estimated_speed_improvement': 25.0,
                'quality_impact': 0.92,
                'implementation_complexity': 'high'
            },
            {
                'strategy': 'model_parameter_tuning',
                'description': 'Optimize model parameters for efficiency',
                'estimated_cost_reduction': 12.0,
                'estimated_speed_improvement': 15.0,
                'quality_impact': 0.98,
                'implementation_complexity': 'medium'
            },
            {
                'strategy': 'parallel_processing_optimization',
                'description': 'Optimize parallel processing configuration',
                'estimated_cost_reduction': 8.0,
                'estimated_speed_improvement': 35.0,
                'quality_impact': 1.0,
                'implementation_complexity': 'low'
            }
        ]
        
        # Filter strategies that meet quality threshold
        viable_strategies = [
            strategy for strategy in optimization_strategies
            if strategy['quality_impact'] >= self.quality_threshold
        ]
        
        # Select strategies to meet savings target
        recommended_strategies = []
        total_cost_reduction = 0
        total_speed_improvement = 0
        
        for strategy in viable_strategies:
            if total_cost_reduction < self.target_savings_percentage:
                recommended_strategies.append(strategy)
                total_cost_reduction += strategy['estimated_cost_reduction']
                total_speed_improvement += strategy['estimated_speed_improvement']
        
        # Calculate new metrics
        actual_cost_reduction = min(total_cost_reduction, self.target_savings_percentage)
        estimated_new_processing_cost = current_processing_cost * (1 - actual_cost_reduction / 100)
        estimated_new_processing_time = current_processing_time * (1 - min(total_speed_improvement, 50) / 100)
        
        result = {
            'optimization_type': 'model_efficiency',
            'optimization_date': target_date,
            'dry_run': self.dry_run,
            'baseline_metrics': {
                'current_processing_cost': current_processing_cost,
                'current_processing_time_ms': current_processing_time,
                'language_breakdown': language_breakdown
            },
            'optimization_analysis': {
                'target_savings_percentage': self.target_savings_percentage,
                'achievable_cost_reduction': actual_cost_reduction,
                'achievable_speed_improvement': min(total_speed_improvement, 50),
                'estimated_new_processing_cost': estimated_new_processing_cost,
                'estimated_new_processing_time_ms': estimated_new_processing_time,
                'cost_savings': current_processing_cost - estimated_new_processing_cost
            },
            'recommended_strategies': recommended_strategies,
            'implementation_plan': self._create_implementation_plan(recommended_strategies),
            'performance_impact': {
                'speed_improvement_percentage': min(total_speed_improvement, 50),
                'throughput_improvement': 'high' if total_speed_improvement > 30 else 'medium',
                'resource_efficiency_gain': actual_cost_reduction
            }
        }
        
        return result
    
    def _optimize_batch_processing(self, baseline_data: Dict[str, Any], target_date: str) -> Dict[str, Any]:
        """Optimize batch processing parameters"""
        current_total_cost = baseline_data.get('cost_data', {}).get('total_daily_cost', 0)
        stories_processed = baseline_data.get('performance_data', {}).get('stories_processed', 0)
        chunks_generated = baseline_data.get('performance_data', {}).get('chunks_generated', 0)
        
        # Current batch configuration analysis
        current_config = {
            'bronze_batch_size': 100,
            'silver_batch_size': 50,
            'embedding_batch_size': 32,
            'parallel_workers': 3
        }
        
        # Optimization recommendations
        optimized_config = {
            'bronze_batch_size': 150,   # Increase for better throughput
            'silver_batch_size': 75,    # Increase for cost efficiency
            'embedding_batch_size': 64, # Increase for API efficiency
            'parallel_workers': 5       # Increase for better parallelization
        }
        
        # Calculate expected improvements
        expected_improvements = {
            'cost_reduction_percentage': 18.5,
            'processing_time_reduction_percentage': 25.3,
            'throughput_improvement_percentage': 32.0,
            'api_calls_reduction_percentage': 22.0
        }
        
        # Calculate new metrics
        estimated_new_cost = current_total_cost * (1 - expected_improvements['cost_reduction_percentage'] / 100)
        estimated_cost_savings = current_total_cost - estimated_new_cost
        
        result = {
            'optimization_type': 'batch_optimization',
            'optimization_date': target_date,
            'dry_run': self.dry_run,
            'baseline_metrics': {
                'current_total_cost': current_total_cost,
                'stories_processed': stories_processed,
                'chunks_generated': chunks_generated,
                'current_batch_config': current_config
            },
            'optimization_analysis': {
                'optimized_batch_config': optimized_config,
                'expected_improvements': expected_improvements,
                'estimated_new_cost': estimated_new_cost,
                'estimated_cost_savings': estimated_cost_savings,
                'configuration_changes': self._calculate_config_changes(current_config, optimized_config)
            },
            'implementation_plan': {
                'phase_1': 'Gradually increase batch sizes by 25%',
                'phase_2': 'Add additional parallel workers',
                'phase_3': 'Fine-tune based on performance metrics',
                'rollback_plan': 'Revert to previous configuration if issues arise',
                'monitoring_metrics': ['processing_time', 'error_rates', 'cost_per_batch', 'memory_usage']
            },
            'risk_assessment': {
                'implementation_risk': 'low',
                'performance_risk': 'low',
                'quality_risk': 'minimal',
                'recommended_rollout': 'gradual'
            }
        }
        
        return result
    
    def _optimize_quality_cost_balance(self, baseline_data: Dict[str, Any], target_date: str) -> Dict[str, Any]:
        """Optimize the balance between quality and cost"""
        current_quality_score = baseline_data.get('quality_data', {}).get('quality_score', 0)
        current_total_cost = baseline_data.get('cost_data', {}).get('total_daily_cost', 0)
        
        # Quality-cost trade-off scenarios
        scenarios = [
            {
                'scenario': 'cost_optimized',
                'description': 'Prioritize cost savings with minimal quality impact',
                'quality_threshold': 0.85,
                'expected_cost_reduction': 25.0,
                'expected_quality_change': -0.05,
                'strategies': ['sentence_transformers', 'batch_optimization', 'smart_routing']
            },
            {
                'scenario': 'balanced',
                'description': 'Balance cost and quality improvements',
                'quality_threshold': 0.90,
                'expected_cost_reduction': 15.0,
                'expected_quality_change': 0.02,
                'strategies': ['selective_optimization', 'quality_monitoring', 'adaptive_thresholds']
            },
            {
                'scenario': 'quality_focused',
                'description': 'Prioritize quality with moderate cost increases',
                'quality_threshold': 0.95,
                'expected_cost_reduction': 5.0,
                'expected_quality_change': 0.08,
                'strategies': ['premium_models', 'enhanced_validation', 'quality_first_routing']
            }
        ]
        
        # Select optimal scenario based on current quality and target savings
        optimal_scenario = None
        for scenario in scenarios:
            if (current_quality_score + scenario['expected_quality_change']) >= self.quality_threshold:
                if scenario['expected_cost_reduction'] >= (self.target_savings_percentage * 0.7):  # 70% of target
                    optimal_scenario = scenario
                    break
        
        if not optimal_scenario:
            optimal_scenario = scenarios[1]  # Default to balanced approach
        
        # Calculate optimized metrics
        estimated_new_quality = current_quality_score + optimal_scenario['expected_quality_change']
        estimated_new_cost = current_total_cost * (1 - optimal_scenario['expected_cost_reduction'] / 100)
        
        result = {
            'optimization_type': 'quality_cost_balance',
            'optimization_date': target_date,
            'dry_run': self.dry_run,
            'baseline_metrics': {
                'current_quality_score': current_quality_score,
                'current_total_cost': current_total_cost,
                'quality_threshold': self.quality_threshold,
                'target_savings_percentage': self.target_savings_percentage
            },
            'optimization_analysis': {
                'selected_scenario': optimal_scenario['scenario'],
                'scenario_description': optimal_scenario['description'],
                'estimated_new_quality_score': estimated_new_quality,
                'estimated_new_cost': estimated_new_cost,
                'quality_change': optimal_scenario['expected_quality_change'],
                'cost_reduction_percentage': optimal_scenario['expected_cost_reduction'],
                'cost_savings': current_total_cost - estimated_new_cost
            },
            'all_scenarios': scenarios,
            'recommended_strategies': optimal_scenario['strategies'],
            'quality_assurance': {
                'quality_monitoring_plan': 'Implement real-time quality tracking',
                'fallback_mechanisms': 'Automatic rollback if quality drops below threshold',
                'quality_validation_frequency': 'Every 4 hours during implementation'
            }
        }
        
        return result
    
    def _create_implementation_plan(self, strategies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create implementation plan for optimization strategies"""
        # Sort strategies by complexity and impact
        low_complexity = [s for s in strategies if s.get('implementation_complexity') == 'low']
        medium_complexity = [s for s in strategies if s.get('implementation_complexity') == 'medium']
        high_complexity = [s for s in strategies if s.get('implementation_complexity') == 'high']
        
        implementation_plan = {
            'phase_1_immediate': {
                'duration': '1-2 days',
                'strategies': low_complexity,
                'description': 'Quick wins with minimal implementation effort'
            },
            'phase_2_short_term': {
                'duration': '1-2 weeks',
                'strategies': medium_complexity,
                'description': 'Medium complexity optimizations with significant impact'
            },
            'phase_3_long_term': {
                'duration': '3-4 weeks',
                'strategies': high_complexity,
                'description': 'Complex optimizations requiring substantial development'
            },
            'monitoring_plan': {
                'metrics_to_track': ['cost_per_story', 'processing_time', 'quality_score', 'error_rates'],
                'monitoring_frequency': 'Every 2 hours during implementation',
                'alert_thresholds': {
                    'cost_increase': '> 5%',
                    'quality_decrease': '> 2%',
                    'error_rate_increase': '> 1%'
                }
            },
            'rollback_criteria': [
                'Cost increase > 10%',
                'Quality decrease > 5%',
                'Error rate > 2%',
                'Processing time increase > 20%'
            ]
        }
        
        return implementation_plan
    
    def _calculate_config_changes(self, current_config: Dict[str, int], optimized_config: Dict[str, int]) -> Dict[str, Any]:
        """Calculate configuration changes and their impact"""
        changes = {}
        
        for key in current_config:
            current_value = current_config[key]
            optimized_value = optimized_config[key]
            change_percentage = ((optimized_value - current_value) / current_value) * 100
            
            changes[key] = {
                'current_value': current_value,
                'optimized_value': optimized_value,
                'change_absolute': optimized_value - current_value,
                'change_percentage': change_percentage,
                'impact_level': 'high' if abs(change_percentage) > 30 else 'medium' if abs(change_percentage) > 10 else 'low'
            }
        
        return changes