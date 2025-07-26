"""
Comprehensive Alerting System
Multi-channel alert management for medallion architecture monitoring
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sys
from pathlib import Path

# Add project paths
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.config.config import CONFIG


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertCategory(Enum):
    """Alert categories"""
    COST = "cost"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    HEALTH = "health"
    SECURITY = "security"
    BUSINESS = "business"


class AlertStatus(Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    title: str
    description: str
    severity: AlertSeverity
    category: AlertCategory
    source: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['severity'] = self.severity.value
        data['category'] = self.category.value
        data['status'] = self.status.value
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., ">", "<", ">=", "<=", "=="
    threshold: Union[float, int, str]
    severity: AlertSeverity
    category: AlertCategory
    cooldown_minutes: int = 60
    enabled: bool = True


class AlertManager:
    """
    Comprehensive alert management system
    Handles alert generation, routing, and notification
    """
    
    def __init__(self):
        """Initialize alert manager"""
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_channels: Dict[str, Any] = {}
        self.alert_history: List[Alert] = []
        self.suppression_rules: List[Dict[str, Any]] = []
        
        # Alert statistics
        self.stats = {
            'total_alerts_generated': 0,
            'alerts_by_severity': {severity.value: 0 for severity in AlertSeverity},
            'alerts_by_category': {category.value: 0 for category in AlertCategory},
            'avg_resolution_time_minutes': 0.0,
            'notification_success_rate': 0.0
        }
        
        # Initialize default alert rules
        self._initialize_default_rules()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def _initialize_default_rules(self):
        """Initialize default alert rules for medallion architecture"""
        default_rules = [
            # Cost alerts
            AlertRule(
                name="daily_cost_threshold",
                description="Daily cost exceeds budget threshold",
                metric_name="total_daily_cost",
                condition=">",
                threshold=50.0,
                severity=AlertSeverity.HIGH,
                category=AlertCategory.COST,
                cooldown_minutes=240  # 4 hours
            ),
            AlertRule(
                name="cost_spike_detection",
                description="Cost spike detected (>20% increase)",
                metric_name="cost_spike_percentage",
                condition=">",
                threshold=20.0,
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.COST,
                cooldown_minutes=120
            ),
            
            # Quality alerts
            AlertRule(
                name="bronze_quality_degradation",
                description="Bronze layer quality below threshold",
                metric_name="bronze_quality_score",
                condition="<",
                threshold=0.90,
                severity=AlertSeverity.HIGH,
                category=AlertCategory.QUALITY,
                cooldown_minutes=60
            ),
            AlertRule(
                name="silver_quality_degradation", 
                description="Silver layer quality below threshold",
                metric_name="silver_quality_score",
                condition="<",
                threshold=0.95,
                severity=AlertSeverity.HIGH,
                category=AlertCategory.QUALITY,
                cooldown_minutes=60
            ),
            AlertRule(
                name="gold_quality_degradation",
                description="Gold layer quality below threshold", 
                metric_name="gold_quality_score",
                condition="<",
                threshold=0.98,
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.QUALITY,
                cooldown_minutes=60
            ),
            
            # Performance alerts
            AlertRule(
                name="processing_time_threshold",
                description="Average processing time exceeds threshold",
                metric_name="avg_processing_time_ms",
                condition=">",
                threshold=30000,  # 30 seconds
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.PERFORMANCE,
                cooldown_minutes=30
            ),
            AlertRule(
                name="error_rate_threshold",
                description="Error rate exceeds acceptable threshold",
                metric_name="error_rate_percentage",
                condition=">",
                threshold=5.0,
                severity=AlertSeverity.HIGH,
                category=AlertCategory.PERFORMANCE,
                cooldown_minutes=15
            ),
            
            # Health alerts
            AlertRule(
                name="system_health_degradation",
                description="Overall system health below threshold",
                metric_name="overall_health_score",
                condition="<",
                threshold=0.80,
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.HEALTH,
                cooldown_minutes=30
            ),
            AlertRule(
                name="database_connectivity",
                description="Database connectivity issues detected",
                metric_name="database_connection_status",
                condition="==",
                threshold="disconnected",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.HEALTH,
                cooldown_minutes=10
            ),
            
            # Business alerts
            AlertRule(
                name="data_freshness_alert",
                description="Data freshness exceeds acceptable threshold",
                metric_name="data_freshness_hours",
                condition=">",
                threshold=4.0,
                severity=AlertSeverity.MEDIUM,
                category=AlertCategory.BUSINESS,
                cooldown_minutes=120
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.name] = rule
    
    async def check_metrics_and_generate_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check metrics against alert rules and generate alerts"""
        new_alerts = []
        
        for rule_name, rule in self.alert_rules.items():
            if not rule.enabled:
                continue
            
            # Check if metric exists in provided metrics
            if rule.metric_name not in metrics:
                continue
            
            metric_value = metrics[rule.metric_name]
            
            # Check if alert should be generated
            if self._evaluate_condition(metric_value, rule.condition, rule.threshold):
                # Check cooldown period
                if self._is_in_cooldown(rule_name, rule.cooldown_minutes):
                    continue
                
                # Generate alert
                alert = await self._generate_alert(rule, metric_value, metrics)
                new_alerts.append(alert)
                
                # Store alert
                self.alerts[alert.id] = alert
                self.alert_history.append(alert)
                
                # Update statistics
                self._update_alert_stats(alert)
                
                self.logger.info(f"Generated alert: {alert.title} (severity: {alert.severity.value})")
        
        return new_alerts
    
    def _evaluate_condition(self, value: Any, condition: str, threshold: Any) -> bool:
        """Evaluate if metric value meets alert condition"""
        try:
            if condition == ">":
                return float(value) > float(threshold)
            elif condition == "<":
                return float(value) < float(threshold)
            elif condition == ">=":
                return float(value) >= float(threshold)
            elif condition == "<=":
                return float(value) <= float(threshold)
            elif condition == "==":
                return str(value) == str(threshold)
            elif condition == "!=":
                return str(value) != str(threshold)
            else:
                self.logger.warning(f"Unknown condition: {condition}")
                return False
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error evaluating condition {condition}: {e}")
            return False
    
    def _is_in_cooldown(self, rule_name: str, cooldown_minutes: int) -> bool:
        """Check if rule is in cooldown period"""
        cooldown_threshold = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
        
        # Check recent alerts for this rule
        for alert in reversed(self.alert_history):
            if (alert.timestamp > cooldown_threshold and 
                alert.metadata and 
                alert.metadata.get('rule_name') == rule_name):
                return True
        
        return False
    
    async def _generate_alert(self, rule: AlertRule, metric_value: Any, all_metrics: Dict[str, Any]) -> Alert:
        """Generate alert from rule and metric data"""
        alert_id = f"{rule.name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        alert = Alert(
            id=alert_id,
            title=f"{rule.description}",
            description=self._generate_alert_description(rule, metric_value, all_metrics),
            severity=rule.severity,
            category=rule.category,
            source="medallion_pipeline",
            timestamp=datetime.now(timezone.utc),
            metadata={
                'rule_name': rule.name,
                'metric_name': rule.metric_name,
                'metric_value': metric_value,
                'threshold': rule.threshold,
                'condition': rule.condition,
                'all_metrics': all_metrics
            }
        )
        
        return alert
    
    def _generate_alert_description(self, rule: AlertRule, metric_value: Any, all_metrics: Dict[str, Any]) -> str:
        """Generate detailed alert description"""
        base_description = f"{rule.description}\n\n"
        base_description += f"Metric: {rule.metric_name}\n"
        base_description += f"Current Value: {metric_value}\n"
        base_description += f"Threshold: {rule.threshold}\n"
        base_description += f"Condition: {rule.condition}\n"
        
        # Add contextual information based on category
        if rule.category == AlertCategory.COST:
            base_description += f"\nDaily Budget: $50.00\n"
            if 'budget_utilization_percentage' in all_metrics:
                base_description += f"Budget Utilization: {all_metrics['budget_utilization_percentage']:.1f}%\n"
        
        elif rule.category == AlertCategory.QUALITY:
            base_description += f"\nQuality Impact: Data processing quality has degraded\n"
            if 'failed_checks' in all_metrics:
                base_description += f"Failed Checks: {all_metrics['failed_checks']}\n"
        
        elif rule.category == AlertCategory.PERFORMANCE:
            base_description += f"\nPerformance Impact: System performance has degraded\n"
            if 'throughput' in all_metrics:
                base_description += f"Current Throughput: {all_metrics['throughput']}\n"
        
        base_description += f"\nTimestamp: {datetime.now(timezone.utc).isoformat()}"
        
        return base_description
    
    async def send_notifications(self, alerts: List[Alert]) -> Dict[str, Any]:
        """Send notifications for alerts through configured channels"""
        notification_results = {
            'total_alerts': len(alerts),
            'notifications_sent': 0,
            'notifications_failed': 0,
            'channel_results': {}
        }
        
        for alert in alerts:
            # Determine notification channels based on severity
            channels = self._get_notification_channels_for_alert(alert)
            
            for channel in channels:
                try:
                    success = await self._send_notification(alert, channel)
                    if success:
                        notification_results['notifications_sent'] += 1
                    else:
                        notification_results['notifications_failed'] += 1
                    
                    if channel not in notification_results['channel_results']:
                        notification_results['channel_results'][channel] = {'sent': 0, 'failed': 0}
                    
                    if success:
                        notification_results['channel_results'][channel]['sent'] += 1
                    else:
                        notification_results['channel_results'][channel]['failed'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Notification failed for {channel}: {e}")
                    notification_results['notifications_failed'] += 1
        
        # Update success rate
        total_notifications = notification_results['notifications_sent'] + notification_results['notifications_failed']
        if total_notifications > 0:
            success_rate = notification_results['notifications_sent'] / total_notifications
            self.stats['notification_success_rate'] = success_rate
        
        return notification_results
    
    def _get_notification_channels_for_alert(self, alert: Alert) -> List[str]:
        """Determine which notification channels to use for an alert"""
        channels = []
        
        # Base channels for all alerts
        channels.append('console')
        channels.append('log')
        
        # Severity-based routing
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            channels.extend(['email', 'slack'])
        
        if alert.severity == AlertSeverity.CRITICAL:
            channels.append('pagerduty')  # For critical alerts
        
        # Category-based routing
        if alert.category == AlertCategory.COST:
            channels.append('cost_channel')
        elif alert.category == AlertCategory.QUALITY:
            channels.append('quality_channel')
        elif alert.category == AlertCategory.PERFORMANCE:
            channels.append('performance_channel')
        
        return list(set(channels))  # Remove duplicates
    
    async def _send_notification(self, alert: Alert, channel: str) -> bool:
        """Send notification through specific channel"""
        try:
            if channel == 'console':
                return self._send_console_notification(alert)
            elif channel == 'log':
                return self._send_log_notification(alert)
            elif channel == 'email':
                return await self._send_email_notification(alert)
            elif channel == 'slack':
                return await self._send_slack_notification(alert)
            elif channel == 'pagerduty':
                return await self._send_pagerduty_notification(alert)
            else:
                # Mock other channels
                self.logger.info(f"Mock notification sent to {channel}: {alert.title}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to send notification to {channel}: {e}")
            return False
    
    def _send_console_notification(self, alert: Alert) -> bool:
        """Send notification to console"""
        severity_symbol = {
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.HIGH: "⚠️",
            AlertSeverity.MEDIUM: "🟡",
            AlertSeverity.LOW: "🔵",
            AlertSeverity.INFO: "ℹ️"
        }
        
        symbol = severity_symbol.get(alert.severity, "🔔")
        print(f"\n{symbol} ALERT [{alert.severity.value.upper()}] {symbol}")
        print(f"Title: {alert.title}")
        print(f"Category: {alert.category.value}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Description: {alert.description}")
        print("-" * 60)
        
        return True
    
    def _send_log_notification(self, alert: Alert) -> bool:
        """Send notification to log file"""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.INFO: logging.INFO
        }
        
        level = log_level.get(alert.severity, logging.INFO)
        self.logger.log(level, f"ALERT: {alert.title} | {alert.description}")
        
        return True
    
    async def _send_email_notification(self, alert: Alert) -> bool:
        """Send email notification (mock implementation)"""
        # In a real implementation, this would use an email service
        email_content = {
            'to': ['ops-team@example.com', 'data-team@example.com'],
            'subject': f"[{alert.severity.value.upper()}] {alert.title}",
            'body': self._format_email_body(alert),
            'alert_id': alert.id
        }
        
        self.logger.info(f"Email notification prepared: {email_content['subject']}")
        return True  # Mock success
    
    async def _send_slack_notification(self, alert: Alert) -> bool:
        """Send Slack notification (mock implementation)"""
        # In a real implementation, this would use Slack API
        slack_message = {
            'channel': '#medallion-alerts',
            'text': f"*{alert.title}*",
            'attachments': [
                {
                    'color': self._get_slack_color(alert.severity),
                    'fields': [
                        {'title': 'Severity', 'value': alert.severity.value, 'short': True},
                        {'title': 'Category', 'value': alert.category.value, 'short': True},
                        {'title': 'Time', 'value': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), 'short': True}
                    ],
                    'text': alert.description
                }
            ]
        }
        
        self.logger.info(f"Slack notification prepared for channel {slack_message['channel']}")
        return True  # Mock success
    
    async def _send_pagerduty_notification(self, alert: Alert) -> bool:
        """Send PagerDuty notification (mock implementation)"""
        # In a real implementation, this would use PagerDuty API
        pagerduty_event = {
            'routing_key': 'medallion-pipeline-key',
            'event_action': 'trigger',
            'payload': {
                'summary': alert.title,
                'severity': alert.severity.value,
                'source': alert.source,
                'component': alert.category.value,
                'custom_details': alert.metadata
            }
        }
        
        self.logger.info(f"PagerDuty notification prepared: {alert.title}")
        return True  # Mock success
    
    def _format_email_body(self, alert: Alert) -> str:
        """Format email body for alert notification"""
        body = f"""
        <html>
        <body>
            <h2>Alert Notification</h2>
            <p><strong>Alert ID:</strong> {alert.id}</p>
            <p><strong>Title:</strong> {alert.title}</p>
            <p><strong>Severity:</strong> {alert.severity.value.upper()}</p>
            <p><strong>Category:</strong> {alert.category.value}</p>
            <p><strong>Timestamp:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            
            <h3>Description</h3>
            <pre>{alert.description}</pre>
            
            <h3>Recommended Actions</h3>
            <ul>
        """
        
        # Add category-specific recommendations
        if alert.category == AlertCategory.COST:
            body += """
                <li>Review cost optimization opportunities</li>
                <li>Check for unexpected usage spikes</li>
                <li>Consider adjusting batch sizes or model selection</li>
            """
        elif alert.category == AlertCategory.QUALITY:
            body += """
                <li>Investigate data quality pipeline</li>
                <li>Check data source connectivity</li>
                <li>Review processing parameters</li>
            """
        elif alert.category == AlertCategory.PERFORMANCE:
            body += """
                <li>Check system resource utilization</li>
                <li>Review processing bottlenecks</li>
                <li>Consider scaling resources</li>
            """
        
        body += """
            </ul>
            
            <p><strong>Dashboard:</strong> <a href="http://monitoring.example.com/medallion">View Dashboard</a></p>
        </body>
        </html>
        """
        
        return body
    
    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """Get Slack color for alert severity"""
        colors = {
            AlertSeverity.CRITICAL: 'danger',
            AlertSeverity.HIGH: 'warning',
            AlertSeverity.MEDIUM: '#ffcc00',
            AlertSeverity.LOW: 'good',
            AlertSeverity.INFO: '#36a64f'
        }
        return colors.get(severity, 'good')
    
    def _update_alert_stats(self, alert: Alert):
        """Update alert statistics"""
        self.stats['total_alerts_generated'] += 1
        self.stats['alerts_by_severity'][alert.severity.value] += 1
        self.stats['alerts_by_category'][alert.category.value] += 1
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.ACKNOWLEDGED
            self.alerts[alert_id].metadata['acknowledged_by'] = acknowledged_by
            self.alerts[alert_id].metadata['acknowledged_at'] = datetime.now(timezone.utc).isoformat()
            
            self.logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        
        return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str = "") -> bool:
        """Resolve an alert"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.RESOLVED
            self.alerts[alert_id].metadata['resolved_by'] = resolved_by
            self.alerts[alert_id].metadata['resolved_at'] = datetime.now(timezone.utc).isoformat()
            self.alerts[alert_id].metadata['resolution_notes'] = resolution_notes
            
            self.logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return True
        
        return False
    
    def get_active_alerts(self, severity_filter: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts with optional severity filter"""
        active_alerts = [
            alert for alert in self.alerts.values()
            if alert.status == AlertStatus.ACTIVE
        ]
        
        if severity_filter:
            active_alerts = [
                alert for alert in active_alerts
                if alert.severity == severity_filter
            ]
        
        return sorted(active_alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get comprehensive alert statistics"""
        active_alerts = self.get_active_alerts()
        
        stats = self.stats.copy()
        stats.update({
            'active_alerts_count': len(active_alerts),
            'active_alerts_by_severity': {},
            'active_alerts_by_category': {},
            'oldest_active_alert': None,
            'newest_active_alert': None
        })
        
        # Calculate active alert statistics
        for severity in AlertSeverity:
            stats['active_alerts_by_severity'][severity.value] = len([
                alert for alert in active_alerts if alert.severity == severity
            ])
        
        for category in AlertCategory:
            stats['active_alerts_by_category'][category.value] = len([
                alert for alert in active_alerts if alert.category == category
            ])
        
        # Find oldest and newest active alerts
        if active_alerts:
            sorted_alerts = sorted(active_alerts, key=lambda x: x.timestamp)
            stats['oldest_active_alert'] = sorted_alerts[0].to_dict()
            stats['newest_active_alert'] = sorted_alerts[-1].to_dict()
        
        return stats


# CLI interface for testing
async def main():
    """Test CLI for alert manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Alert Manager")
    parser.add_argument('--test-alerts', action='store_true', help='Generate test alerts')
    parser.add_argument('--stats', action='store_true', help='Show alert statistics')
    
    args = parser.parse_args()
    
    alert_manager = AlertManager()
    
    try:
        if args.test_alerts:
            # Generate test metrics that will trigger alerts
            test_metrics = {
                'total_daily_cost': 65.0,  # Over $50 threshold
                'bronze_quality_score': 0.85,  # Below 0.90 threshold
                'avg_processing_time_ms': 35000,  # Over 30000ms threshold
                'error_rate_percentage': 7.5,  # Over 5% threshold
                'overall_health_score': 0.75,  # Below 0.80 threshold
                'data_freshness_hours': 6.0  # Over 4 hours threshold
            }
            
            print("🧪 Generating test alerts...")
            alerts = await alert_manager.check_metrics_and_generate_alerts(test_metrics)
            
            print(f"Generated {len(alerts)} alerts")
            
            # Send notifications
            if alerts:
                print("📨 Sending notifications...")
                notification_results = await alert_manager.send_notifications(alerts)
                print(f"Notification results: {notification_results}")
        
        if args.stats:
            stats = alert_manager.get_alert_statistics()
            print(f"📊 Alert Statistics: {json.dumps(stats, indent=2)}")
        
        # Show active alerts
        active_alerts = alert_manager.get_active_alerts()
        if active_alerts:
            print(f"\n🚨 Active Alerts ({len(active_alerts)}):")
            for alert in active_alerts[:5]:  # Show first 5
                print(f"   {alert.severity.value.upper()}: {alert.title}")
        
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user")
    except Exception as e:
        print(f"❌ Alert manager error: {e}")


if __name__ == "__main__":
    asyncio.run(main())