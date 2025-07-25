"""
Metrics Dashboard
Real-time monitoring dashboard for medallion architecture
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.processing.config import CONFIG


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MetricSeries:
    """Time series of metric data"""
    name: str
    description: str
    unit: str
    data_points: List[MetricPoint]
    tags: Optional[Dict[str, str]] = None


class MetricsCollector:
    """
    Metrics collection and aggregation system
    Collects metrics from all medallion pipeline components
    """
    
    def __init__(self):
        """Initialize metrics collector"""
        self.metrics: Dict[str, MetricSeries] = {}
        self.collection_interval_seconds = 60
        self.retention_hours = 24
        self.running = False
        
        # Metric definitions
        self.metric_definitions = {
            # Cost metrics
            'total_daily_cost': {
                'description': 'Total daily processing cost in USD',
                'unit': 'USD',
                'tags': {'category': 'cost'}
            },
            'cost_per_story': {
                'description': 'Cost per story processed',
                'unit': 'USD',
                'tags': {'category': 'cost'}
            },
            'embedding_cost': {
                'description': 'Cost of embedding generation',
                'unit': 'USD',
                'tags': {'category': 'cost', 'component': 'embedding'}
            },
            
            # Quality metrics
            'bronze_quality_score': {
                'description': 'Bronze layer data quality score',
                'unit': 'score',
                'tags': {'category': 'quality', 'layer': 'bronze'}
            },
            'silver_quality_score': {
                'description': 'Silver layer data quality score',
                'unit': 'score',
                'tags': {'category': 'quality', 'layer': 'silver'}
            },
            'gold_quality_score': {
                'description': 'Gold layer data quality score',
                'unit': 'score',
                'tags': {'category': 'quality', 'layer': 'gold'}
            },
            
            # Performance metrics
            'avg_processing_time_ms': {
                'description': 'Average story processing time',
                'unit': 'milliseconds',
                'tags': {'category': 'performance'}
            },
            'throughput_stories_per_minute': {
                'description': 'Stories processed per minute',
                'unit': 'stories/min',
                'tags': {'category': 'performance'}
            },
            'error_rate_percentage': {
                'description': 'Processing error rate',
                'unit': 'percentage',
                'tags': {'category': 'performance'}
            },
            
            # Business metrics
            'stories_processed_daily': {
                'description': 'Number of stories processed daily',
                'unit': 'count',
                'tags': {'category': 'business'}
            },
            'chunks_generated_daily': {
                'description': 'Number of chunks generated daily',
                'unit': 'count',
                'tags': {'category': 'business'}
            },
            'active_users': {
                'description': 'Number of active users',
                'unit': 'count',
                'tags': {'category': 'business'}
            },
            
            # System health metrics
            'overall_health_score': {
                'description': 'Overall system health score',
                'unit': 'score',
                'tags': {'category': 'health'}
            },
            'database_connection_health': {
                'description': 'Database connection health',
                'unit': 'score',
                'tags': {'category': 'health', 'component': 'database'}
            },
            'model_api_health': {
                'description': 'Model API health score',
                'unit': 'score',
                'tags': {'category': 'health', 'component': 'model_api'}
            }
        }
        
        # Initialize metric series
        for metric_name, definition in self.metric_definitions.items():
            self.metrics[metric_name] = MetricSeries(
                name=metric_name,
                description=definition['description'],
                unit=definition['unit'],
                data_points=[],
                tags=definition['tags']
            )
    
    async def start_collection(self):
        """Start metrics collection"""
        self.running = True
        print(f"🚀 Starting metrics collection (interval: {self.collection_interval_seconds}s)")
        
        while self.running:
            try:
                await self._collect_metrics()
                await self._cleanup_old_metrics()
                await asyncio.sleep(self.collection_interval_seconds)
            except Exception as e:
                print(f"❌ Error in metrics collection: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.running = False
        print("🛑 Stopping metrics collection")
    
    async def _collect_metrics(self):
        """Collect current metrics from all sources"""
        timestamp = datetime.now(timezone.utc)
        
        # In a real implementation, these would query actual systems
        # For now, we'll generate mock data with realistic patterns
        
        # Cost metrics (with daily patterns)
        base_cost = 45.0
        time_factor = (timestamp.hour / 24.0)  # Vary by time of day
        daily_cost = base_cost + (10.0 * time_factor) + (5.0 * (0.5 - abs(0.5 - time_factor)))
        
        await self._record_metric('total_daily_cost', daily_cost, timestamp)
        await self._record_metric('cost_per_story', daily_cost / max(150, 1), timestamp)
        await self._record_metric('embedding_cost', daily_cost * 0.65, timestamp)
        
        # Quality metrics (generally stable with occasional dips)
        import random
        quality_base = 0.92
        quality_noise = random.uniform(-0.05, 0.02)
        
        await self._record_metric('bronze_quality_score', min(1.0, quality_base + quality_noise), timestamp)
        await self._record_metric('silver_quality_score', min(1.0, quality_base + 0.03 + quality_noise), timestamp)
        await self._record_metric('gold_quality_score', min(1.0, quality_base + 0.06 + quality_noise), timestamp)
        
        # Performance metrics (varying throughout the day)
        base_processing_time = 25000  # 25 seconds
        load_factor = 1.0 + (0.5 * time_factor)  # Higher load during day
        processing_time = base_processing_time * load_factor
        
        await self._record_metric('avg_processing_time_ms', processing_time, timestamp)
        await self._record_metric('throughput_stories_per_minute', 60000 / processing_time, timestamp)
        await self._record_metric('error_rate_percentage', max(0, 2.0 + random.uniform(-1.0, 3.0)), timestamp)
        
        # Business metrics
        daily_stories = int(150 + (50 * time_factor))
        await self._record_metric('stories_processed_daily', daily_stories, timestamp)
        await self._record_metric('chunks_generated_daily', daily_stories * 12, timestamp)
        await self._record_metric('active_users', max(1, int(25 + (15 * time_factor) + random.uniform(-5, 5))), timestamp)
        
        # Health metrics
        health_base = 0.88
        health_variation = random.uniform(-0.05, 0.05)
        await self._record_metric('overall_health_score', min(1.0, max(0.0, health_base + health_variation)), timestamp)
        await self._record_metric('database_connection_health', min(1.0, 0.95 + random.uniform(-0.02, 0.02)), timestamp)
        await self._record_metric('model_api_health', min(1.0, 0.90 + random.uniform(-0.05, 0.05)), timestamp)
    
    async def _record_metric(self, metric_name: str, value: float, timestamp: datetime):
        """Record a single metric value"""
        if metric_name in self.metrics:
            metric_point = MetricPoint(
                timestamp=timestamp,
                value=value,
                metadata={'collection_method': 'automated'}
            )
            self.metrics[metric_name].data_points.append(metric_point)
    
    async def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        
        for metric_series in self.metrics.values():
            metric_series.data_points = [
                point for point in metric_series.data_points
                if point.timestamp > cutoff_time
            ]
    
    def get_metric_current_value(self, metric_name: str) -> Optional[float]:
        """Get current value of a metric"""
        if metric_name in self.metrics and self.metrics[metric_name].data_points:
            return self.metrics[metric_name].data_points[-1].value
        return None
    
    def get_metric_series(self, metric_name: str, hours: int = 1) -> Optional[MetricSeries]:
        """Get metric series for specified time period"""
        if metric_name not in self.metrics:
            return None
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered_points = [
            point for point in self.metrics[metric_name].data_points
            if point.timestamp > cutoff_time
        ]
        
        return MetricSeries(
            name=self.metrics[metric_name].name,
            description=self.metrics[metric_name].description,
            unit=self.metrics[metric_name].unit,
            data_points=filtered_points,
            tags=self.metrics[metric_name].tags
        )
    
    def get_all_current_metrics(self) -> Dict[str, float]:
        """Get current values for all metrics"""
        current_metrics = {}
        for metric_name in self.metrics:
            value = self.get_metric_current_value(metric_name)
            if value is not None:
                current_metrics[metric_name] = value
        return current_metrics


class DashboardGenerator:
    """
    Generate dashboard views for metrics visualization
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize dashboard generator"""
        self.metrics_collector = metrics_collector
    
    def generate_console_dashboard(self, hours: int = 1) -> str:
        """Generate console-based dashboard"""
        dashboard = []
        dashboard.append("=" * 80)
        dashboard.append("🏛️  MEDALLION ARCHITECTURE MONITORING DASHBOARD")
        dashboard.append("=" * 80)
        dashboard.append(f"📅 Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        dashboard.append(f"⏰ Time Range: Last {hours} hour(s)")
        dashboard.append("")
        
        # Cost Overview
        dashboard.append("💰 COST METRICS")
        dashboard.append("-" * 40)
        cost_metrics = ['total_daily_cost', 'cost_per_story', 'embedding_cost']
        for metric in cost_metrics:
            value = self.metrics_collector.get_metric_current_value(metric)
            if value is not None:
                unit = self.metrics_collector.metrics[metric].unit
                dashboard.append(f"   {metric:<25}: {value:8.2f} {unit}")
        dashboard.append("")
        
        # Quality Overview
        dashboard.append("📊 QUALITY METRICS")
        dashboard.append("-" * 40)
        quality_metrics = ['bronze_quality_score', 'silver_quality_score', 'gold_quality_score']
        for metric in quality_metrics:
            value = self.metrics_collector.get_metric_current_value(metric)
            if value is not None:
                status = "✅" if value >= 0.9 else "⚠️" if value >= 0.8 else "❌"
                dashboard.append(f"   {metric:<25}: {value:8.3f} {status}")
        dashboard.append("")
        
        # Performance Overview
        dashboard.append("⚡ PERFORMANCE METRICS")
        dashboard.append("-" * 40)
        perf_metrics = ['avg_processing_time_ms', 'throughput_stories_per_minute', 'error_rate_percentage']
        for metric in perf_metrics:
            value = self.metrics_collector.get_metric_current_value(metric)
            if value is not None:
                unit = self.metrics_collector.metrics[metric].unit
                dashboard.append(f"   {metric:<25}: {value:8.2f} {unit}")
        dashboard.append("")
        
        # Business Overview
        dashboard.append("📈 BUSINESS METRICS")
        dashboard.append("-" * 40)
        business_metrics = ['stories_processed_daily', 'chunks_generated_daily', 'active_users']
        for metric in business_metrics:
            value = self.metrics_collector.get_metric_current_value(metric)
            if value is not None:
                unit = self.metrics_collector.metrics[metric].unit
                dashboard.append(f"   {metric:<25}: {value:8.0f} {unit}")
        dashboard.append("")
        
        # Health Overview
        dashboard.append("🏥 HEALTH METRICS")
        dashboard.append("-" * 40)
        health_metrics = ['overall_health_score', 'database_connection_health', 'model_api_health']
        for metric in health_metrics:
            value = self.metrics_collector.get_metric_current_value(metric)
            if value is not None:
                status = "✅" if value >= 0.9 else "⚠️" if value >= 0.7 else "❌"
                dashboard.append(f"   {metric:<25}: {value:8.3f} {status}")
        dashboard.append("")
        
        # System Status Summary
        dashboard.append("🎯 SYSTEM STATUS SUMMARY")
        dashboard.append("-" * 40)
        
        # Calculate overall status
        cost = self.metrics_collector.get_metric_current_value('total_daily_cost') or 0
        quality = self.metrics_collector.get_metric_current_value('overall_health_score') or 0
        error_rate = self.metrics_collector.get_metric_current_value('error_rate_percentage') or 0
        
        cost_status = "✅" if cost <= 50 else "⚠️" if cost <= 60 else "❌"
        quality_status = "✅" if quality >= 0.9 else "⚠️" if quality >= 0.8 else "❌"
        error_status = "✅" if error_rate <= 5 else "⚠️" if error_rate <= 10 else "❌"
        
        dashboard.append(f"   Cost Budget Status      : {cost_status} ${cost:.2f}/day (Budget: $50/day)")
        dashboard.append(f"   Quality Status          : {quality_status} {quality:.3f} (Target: >0.9)")
        dashboard.append(f"   Error Rate Status       : {error_status} {error_rate:.1f}% (Target: <5%)")
        
        # Determine overall system status
        status_scores = [cost <= 50, quality >= 0.8, error_rate <= 10]
        if all(status_scores):
            overall_status = "🟢 HEALTHY"
        elif sum(status_scores) >= 2:
            overall_status = "🟡 DEGRADED"
        else:
            overall_status = "🔴 CRITICAL"
        
        dashboard.append(f"   Overall System Status   : {overall_status}")
        dashboard.append("")
        
        # Recent trends
        dashboard.append("📈 RECENT TRENDS (Last Hour)")
        dashboard.append("-" * 40)
        
        trend_metrics = ['total_daily_cost', 'bronze_quality_score', 'avg_processing_time_ms']
        for metric in trend_metrics:
            series = self.metrics_collector.get_metric_series(metric, hours=1)
            if series and len(series.data_points) >= 2:
                recent_value = series.data_points[-1].value
                previous_value = series.data_points[0].value
                change = recent_value - previous_value
                change_pct = (change / max(previous_value, 0.01)) * 100
                
                trend_arrow = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                dashboard.append(f"   {metric:<25}: {trend_arrow} {change_pct:+6.1f}%")
        
        dashboard.append("")
        dashboard.append("=" * 80)
        
        return "\n".join(dashboard)
    
    def generate_json_dashboard(self, hours: int = 1) -> Dict[str, Any]:
        """Generate JSON dashboard data for web UI"""
        current_metrics = self.metrics_collector.get_all_current_metrics()
        
        dashboard_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'time_range_hours': hours,
            'current_metrics': current_metrics,
            'metric_series': {},
            'status_summary': self._calculate_status_summary(current_metrics),
            'alerts': [],  # Would integrate with alert system
            'trends': self._calculate_trends(hours)
        }
        
        # Include time series data for key metrics
        key_metrics = [
            'total_daily_cost', 'bronze_quality_score', 'silver_quality_score', 
            'avg_processing_time_ms', 'stories_processed_daily'
        ]
        
        for metric in key_metrics:
            series = self.metrics_collector.get_metric_series(metric, hours)
            if series:
                dashboard_data['metric_series'][metric] = {
                    'name': series.name,
                    'description': series.description,
                    'unit': series.unit,
                    'data_points': [
                        {
                            'timestamp': point.timestamp.isoformat(),
                            'value': point.value
                        }
                        for point in series.data_points
                    ],
                    'tags': series.tags
                }
        
        return dashboard_data
    
    def _calculate_status_summary(self, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Calculate overall status summary"""
        cost = current_metrics.get('total_daily_cost', 0)
        quality = current_metrics.get('overall_health_score', 0)
        error_rate = current_metrics.get('error_rate_percentage', 0)
        
        return {
            'cost_status': {
                'value': cost,
                'threshold': 50.0,
                'status': 'healthy' if cost <= 50 else 'warning' if cost <= 60 else 'critical',
                'budget_utilization_percentage': (cost / 50.0) * 100
            },
            'quality_status': {
                'value': quality,
                'threshold': 0.9,
                'status': 'healthy' if quality >= 0.9 else 'warning' if quality >= 0.8 else 'critical'
            },
            'performance_status': {
                'error_rate': error_rate,
                'error_threshold': 5.0,
                'status': 'healthy' if error_rate <= 5 else 'warning' if error_rate <= 10 else 'critical'
            },
            'overall_status': self._determine_overall_status(cost, quality, error_rate)
        }
    
    def _determine_overall_status(self, cost: float, quality: float, error_rate: float) -> str:
        """Determine overall system status"""
        issues = 0
        
        if cost > 60:  # Critical cost
            issues += 2
        elif cost > 50:  # Warning cost
            issues += 1
        
        if quality < 0.8:  # Critical quality
            issues += 2
        elif quality < 0.9:  # Warning quality
            issues += 1
        
        if error_rate > 10:  # Critical error rate
            issues += 2
        elif error_rate > 5:  # Warning error rate
            issues += 1
        
        if issues == 0:
            return 'healthy'
        elif issues <= 2:
            return 'warning'
        else:
            return 'critical'
    
    def _calculate_trends(self, hours: int) -> Dict[str, Dict[str, float]]:
        """Calculate trends for key metrics"""
        trends = {}
        
        key_metrics = ['total_daily_cost', 'bronze_quality_score', 'avg_processing_time_ms']
        
        for metric in key_metrics:
            series = self.metrics_collector.get_metric_series(metric, hours)
            if series and len(series.data_points) >= 2:
                recent_value = series.data_points[-1].value
                previous_value = series.data_points[0].value
                change = recent_value - previous_value
                change_percentage = (change / max(previous_value, 0.01)) * 100
                
                trends[metric] = {
                    'change_absolute': change,
                    'change_percentage': change_percentage,
                    'direction': 'up' if change > 0 else 'down' if change < 0 else 'stable'
                }
        
        return trends


# CLI interface for testing
async def main():
    """Test CLI for metrics dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Metrics Dashboard")
    parser.add_argument('--collect', action='store_true', help='Start metrics collection')
    parser.add_argument('--dashboard', action='store_true', help='Show dashboard')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--hours', type=int, default=1, help='Hours of data to show')
    
    args = parser.parse_args()
    
    collector = MetricsCollector()
    dashboard = DashboardGenerator(collector)
    
    try:
        if args.collect:
            # Start collection and run for a short time
            print("🚀 Starting metrics collection...")
            collection_task = asyncio.create_task(collector.start_collection())
            
            # Let it collect for a bit
            await asyncio.sleep(5)
            
            collector.stop_collection()
            collection_task.cancel()
            
            try:
                await collection_task
            except asyncio.CancelledError:
                pass
        
        if args.dashboard:
            if args.json:
                dashboard_data = dashboard.generate_json_dashboard(args.hours)
                print(json.dumps(dashboard_data, indent=2))
            else:
                console_dashboard = dashboard.generate_console_dashboard(args.hours)
                print(console_dashboard)
        
        # Show current metrics summary
        current_metrics = collector.get_all_current_metrics()
        if current_metrics:
            print(f"\n📊 Current Metrics Summary:")
            for metric, value in list(current_metrics.items())[:5]:
                print(f"   {metric}: {value:.2f}")
        
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
        collector.stop_collection()
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        collector.stop_collection()


if __name__ == "__main__":
    asyncio.run(main())