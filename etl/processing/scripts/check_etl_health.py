#!/usr/bin/env python3
"""
ETL Pipeline Health Check and Docker Integration Script
Validates all services and dependencies for ETL pipeline execution
"""
import asyncio
import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ETLHealthChecker:
    """
    Comprehensive health checker for ETL pipeline infrastructure
    """
    
    def __init__(self, verbose: bool = False):
        """Initialize health checker"""
        self.verbose = verbose
        self.check_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'unknown',
            'services': {},
            'dependencies': {},
            'recommendations': [],
            'errors': []
        }
        
        # Service configurations
        self.services = {
            'database': {
                'name': 'PostgreSQL Database',
                'required': True,
                'check_function': self._check_database
            },
            'ollama': {
                'name': 'Ollama Model Server',
                'required': True,
                'check_function': self._check_ollama
            },
            'airflow': {
                'name': 'Airflow Web Server',
                'required': False,
                'check_function': self._check_airflow
            },
            'docker': {
                'name': 'Docker Services',
                'required': False,
                'check_function': self._check_docker_services
            }
        }
        
        # Environment dependencies
        self.dependencies = {
            'environment_variables': {
                'name': 'Environment Variables',
                'required': True,
                'check_function': self._check_environment_variables
            },
            'python_packages': {
                'name': 'Python Dependencies',
                'required': True,
                'check_function': self._check_python_packages
            },
            'file_permissions': {
                'name': 'File System Permissions',
                'required': True,
                'check_function': self._check_file_permissions
            },
            'disk_space': {
                'name': 'Disk Space',
                'required': True,
                'check_function': self._check_disk_space
            }
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️ ",
            "SUCCESS": "✅",
            "WARNING": "⚠️ ",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
        
        if self.verbose or level in ["WARNING", "ERROR"]:
            if level == "ERROR":
                self.check_results['errors'].append(message)
    
    async def _check_database(self) -> Tuple[bool, str, Dict]:
        """Check PostgreSQL database connectivity and schema"""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            from dotenv import load_dotenv
            load_dotenv()  # Load environment variables from .env file
            
            # Ensure required environment variables are set
            required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                return False, f"Missing required environment variables: {', '.join(missing_vars)}", {}
            
            # Connection parameters
            conn_params = {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT')),
                'database': os.getenv('DB_NAME'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }
            
            self.log(f"Connecting to database at {conn_params['host']}:{conn_params['port']}")
            
            # Test connection
            conn = psycopg2.connect(**conn_params)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check database version
                cur.execute("SELECT version()")
                version = cur.fetchone()['version']
                
                # Check medallion architecture tables
                required_tables = [
                    'bronze_stories',
                    'bronze_story_processing', 
                    'silver_story_chunks',
                    'gold_layer_metrics'
                ]
                
                missing_tables = []
                table_stats = {}
                
                for table in required_tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cur.fetchone()['count']
                        table_stats[table] = count
                        self.log(f"Table {table}: {count} records", "DEBUG")
                    except psycopg2.Error:
                        missing_tables.append(table)
                
                # Check for indexes
                cur.execute("""
                    SELECT schemaname, indexname, tablename 
                    FROM pg_indexes 
                    WHERE tablename IN ('bronze_stories', 'silver_story_chunks')
                """)
                indexes = cur.fetchall()
                
            conn.close()
            
            # Prepare result
            details = {
                'version': version.split()[1] if version else 'unknown',
                'connection_params': {k: v for k, v in conn_params.items() if k != 'password'},
                'table_stats': table_stats,
                'missing_tables': missing_tables,
                'indexes_count': len(indexes)
            }
            
            if missing_tables:
                return False, f"Missing tables: {', '.join(missing_tables)}", details
            else:
                return True, f"Connected successfully, {len(table_stats)} tables found", details
                
        except ImportError:
            return False, "psycopg2 package not installed", {}
        except Exception as e:
            return False, str(e), {}
    
    async def _check_ollama(self) -> Tuple[bool, str, Dict]:
        """Check Ollama service and models"""
        try:
            ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            self.log(f"Checking Ollama at {ollama_url}")
            
            # Setup session with retries
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Check service availability
            response = session.get(f"{ollama_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            models = models_data.get('models', [])
            model_names = [model['name'] for model in models]
            
            # Check required models
            required_models = ['llama3.2', 'deepseek-coder']
            available_models = []
            missing_models = []
            
            for required in required_models:
                found = any(required in name for name in model_names)
                if found:
                    matching_model = next(name for name in model_names if required in name)
                    available_models.append(matching_model)
                else:
                    missing_models.append(required)
            
            # Test model inference (quick test)
            inference_test = False
            if available_models:
                try:
                    test_response = session.post(
                        f"{ollama_url}/api/generate",
                        json={
                            "model": available_models[0],
                            "prompt": "Hello",
                            "stream": False,
                            "options": {"num_predict": 5}
                        },
                        timeout=30
                    )
                    inference_test = test_response.status_code == 200
                except:
                    inference_test = False
            
            details = {
                'url': ollama_url,
                'total_models': len(models),
                'available_models': available_models,
                'missing_models': missing_models,
                'all_models': model_names,
                'inference_test': inference_test
            }
            
            if missing_models:
                return False, f"Missing required models: {', '.join(missing_models)}", details
            elif not inference_test:
                return False, "Models available but inference test failed", details
            else:
                return True, f"Service ready with {len(available_models)} required models", details
                
        except requests.exceptions.ConnectionError:
            return False, "Service not reachable - is Ollama running?", {}
        except requests.exceptions.Timeout:
            return False, "Service timeout - Ollama may be starting up", {}
        except Exception as e:
            return False, str(e), {}
    
    async def _check_airflow(self) -> Tuple[bool, str, Dict]:
        """Check Airflow web server"""
        try:
            airflow_url = os.getenv('AIRFLOW_URL', 'http://localhost:8080')
            
            self.log(f"Checking Airflow at {airflow_url}")
            
            session = requests.Session()
            session.timeout = 10
            
            # Check health endpoint
            try:
                health_response = session.get(f"{airflow_url}/health")
                health_ok = health_response.status_code == 200
            except:
                health_ok = False
            
            # Check API endpoint
            try:
                api_response = session.get(f"{airflow_url}/api/v1/dags")
                api_ok = api_response.status_code in [200, 401]  # 401 is OK (auth required)
                
                if api_response.status_code == 200:
                    dags_data = api_response.json()
                    total_dags = dags_data.get('total_entries', 0)
                else:
                    total_dags = 'unknown'
            except:
                api_ok = False
                total_dags = 'unknown'
            
            details = {
                'url': airflow_url,
                'health_endpoint': health_ok,
                'api_endpoint': api_ok,
                'total_dags': total_dags
            }
            
            if health_ok and api_ok:
                return True, f"Service accessible, {total_dags} DAGs found", details
            elif health_ok:
                return False, "Health OK but API not accessible", details
            else:
                return False, "Service not accessible", details
                
        except Exception as e:
            return False, str(e), {}
    
    async def _check_docker_services(self) -> Tuple[bool, str, Dict]:
        """Check Docker services status"""
        try:
            # Check if docker-compose is available
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return False, "docker-compose not available", {}
            
            # Check running services
            result = subprocess.run(['docker-compose', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return False, "Could not get service status", {}
            
            # Parse service status
            services = []
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    try:
                        service = json.loads(line)
                        services.append({
                            'name': service.get('Service', 'unknown'),
                            'state': service.get('State', 'unknown'),
                            'status': service.get('Status', 'unknown')
                        })
                    except json.JSONDecodeError:
                        continue
            
            # Check specific services
            important_services = ['hauntbro-db', 'ollama', 'airflow-webserver']
            running_services = [s for s in services if s['state'] == 'running']
            running_service_names = [s['name'] for s in running_services]
            
            missing_important = [s for s in important_services if s not in running_service_names]
            
            details = {
                'total_services': len(services),
                'running_services': len(running_services),
                'services': services,
                'missing_important': missing_important
            }
            
            if missing_important:
                return False, f"Important services not running: {', '.join(missing_important)}", details
            else:
                return True, f"{len(running_services)}/{len(services)} services running", details
                
        except subprocess.TimeoutExpired:
            return False, "Docker command timeout", {}
        except FileNotFoundError:
            return False, "Docker not installed or not in PATH", {}
        except Exception as e:
            return False, str(e), {}
    
    async def _check_environment_variables(self) -> Tuple[bool, str, Dict]:
        """Check required environment variables"""
        required_vars = [
            'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'
        ]
        
        optional_vars = [
            'OLLAMA_BASE_URL', 'OPENAI_API_KEY', 'AIRFLOW_URL'
        ]
        
        missing_required = []
        missing_optional = []
        present_vars = {}
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Don't log passwords
                if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                    present_vars[var] = '***'
                else:
                    present_vars[var] = value
            else:
                missing_required.append(var)
        
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                if 'PASSWORD' in var or 'SECRET' in var or 'KEY' in var:
                    present_vars[var] = '***'
                else:
                    present_vars[var] = value
            else:
                missing_optional.append(var)
        
        details = {
            'required_vars': required_vars,
            'optional_vars': optional_vars,
            'present_vars': present_vars,
            'missing_required': missing_required,
            'missing_optional': missing_optional
        }
        
        if missing_required:
            return False, f"Missing required variables: {', '.join(missing_required)}", details
        else:
            return True, f"{len(present_vars)} variables configured", details
    
    async def _check_python_packages(self) -> Tuple[bool, str, Dict]:
        """Check Python package dependencies"""
        required_packages = [
            'asyncpg', 'psycopg2', 'requests', 'numpy', 'transformers',
            'torch', 'openai', 'jieba', 'zhconv', 'nltk', 'spacy'
        ]
        
        available_packages = []
        missing_packages = []
        package_versions = {}
        
        for package in required_packages:
            try:
                __import__(package)
                available_packages.append(package)
                
                # Try to get version
                try:
                    module = __import__(package)
                    version = getattr(module, '__version__', 'unknown')
                    package_versions[package] = version
                except:
                    package_versions[package] = 'unknown'
                    
            except ImportError:
                missing_packages.append(package)
        
        details = {
            'required_packages': required_packages,
            'available_packages': available_packages,
            'missing_packages': missing_packages,
            'package_versions': package_versions
        }
        
        if missing_packages:
            return False, f"Missing packages: {', '.join(missing_packages)}", details
        else:
            return True, f"{len(available_packages)} packages available", details
    
    async def _check_file_permissions(self) -> Tuple[bool, str, Dict]:
        """Check file system permissions"""
        import tempfile
        import stat
        
        test_results = {}
        issues = []
        
        # Test write permissions in current directory
        try:
            with tempfile.NamedTemporaryFile(delete=True, dir='.') as tmp:
                tmp.write(b"test")
                tmp.flush()
            test_results['current_dir_write'] = True
        except Exception as e:
            test_results['current_dir_write'] = False
            issues.append(f"Cannot write to current directory: {e}")
        
        # Test temp directory
        try:
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp.write(b"test")
                tmp.flush()
            test_results['temp_dir_write'] = True
        except Exception as e:
            test_results['temp_dir_write'] = False
            issues.append(f"Cannot write to temp directory: {e}")
        
        # Check log directory
        log_dir = './logs'
        if os.path.exists(log_dir):
            try:
                test_file = os.path.join(log_dir, 'test_write.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                test_results['log_dir_write'] = True
            except Exception as e:
                test_results['log_dir_write'] = False
                issues.append(f"Cannot write to logs directory: {e}")
        else:
            test_results['log_dir_write'] = 'not_exists'
        
        details = {
            'test_results': test_results,
            'issues': issues
        }
        
        if issues:
            return False, f"{len(issues)} permission issues found", details
        else:
            return True, "All permission tests passed", details
    
    async def _check_disk_space(self) -> Tuple[bool, str, Dict]:
        """Check available disk space"""
        import shutil
        
        try:
            # Check current directory
            total, used, free = shutil.disk_usage('.')
            
            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            used_percent = (used / total) * 100
            
            details = {
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'free_gb': round(free_gb, 2),
                'used_percent': round(used_percent, 1)
            }
            
            # Check if we have enough space (at least 1GB free)
            if free_gb < 1.0:
                return False, f"Low disk space: {free_gb:.2f}GB free", details
            elif used_percent > 90:
                return False, f"Disk usage high: {used_percent:.1f}% used", details
            else:
                return True, f"{free_gb:.2f}GB free ({used_percent:.1f}% used)", details
                
        except Exception as e:
            return False, str(e), {}
    
    async def run_health_checks(self) -> bool:
        """Run all health checks"""
        self.log("🚀 Starting ETL Pipeline Health Check")
        self.log(f"Timestamp: {self.check_results['timestamp']}")
        
        overall_success = True
        
        # Check services
        self.log("\n📋 Checking Services...")
        for service_id, service_config in self.services.items():
            self.log(f"Checking {service_config['name']}...")
            
            try:
                success, message, details = await service_config['check_function']()
                
                self.check_results['services'][service_id] = {
                    'name': service_config['name'],
                    'required': service_config['required'],
                    'status': 'success' if success else 'failed',
                    'message': message,
                    'details': details
                }
                
                if success:
                    self.log(f"{service_config['name']}: {message}", "SUCCESS")
                else:
                    level = "ERROR" if service_config['required'] else "WARNING"
                    self.log(f"{service_config['name']}: {message}", level)
                    if service_config['required']:
                        overall_success = False
                        
            except Exception as e:
                error_msg = f"Health check failed: {str(e)}"
                self.check_results['services'][service_id] = {
                    'name': service_config['name'],
                    'required': service_config['required'],
                    'status': 'error',
                    'message': error_msg,
                    'details': {}
                }
                
                level = "ERROR" if service_config['required'] else "WARNING"
                self.log(f"{service_config['name']}: {error_msg}", level)
                if service_config['required']:
                    overall_success = False
        
        # Check dependencies
        self.log("\n🔧 Checking Dependencies...")
        for dep_id, dep_config in self.dependencies.items():
            self.log(f"Checking {dep_config['name']}...")
            
            try:
                success, message, details = await dep_config['check_function']()
                
                self.check_results['dependencies'][dep_id] = {
                    'name': dep_config['name'],
                    'required': dep_config['required'],
                    'status': 'success' if success else 'failed',
                    'message': message,
                    'details': details
                }
                
                if success:
                    self.log(f"{dep_config['name']}: {message}", "SUCCESS")
                else:
                    level = "ERROR" if dep_config['required'] else "WARNING"
                    self.log(f"{dep_config['name']}: {message}", level)
                    if dep_config['required']:
                        overall_success = False
                        
            except Exception as e:
                error_msg = f"Dependency check failed: {str(e)}"
                self.check_results['dependencies'][dep_id] = {
                    'name': dep_config['name'],
                    'required': dep_config['required'],
                    'status': 'error',
                    'message': error_msg,
                    'details': {}
                }
                
                level = "ERROR" if dep_config['required'] else "WARNING"
                self.log(f"{dep_config['name']}: {error_msg}", level)
                if dep_config['required']:
                    overall_success = False
        
        # Generate recommendations
        self._generate_recommendations()
        
        # Set overall status
        self.check_results['overall_status'] = 'healthy' if overall_success else 'unhealthy'
        
        return overall_success
    
    def _generate_recommendations(self):
        """Generate recommendations based on check results"""
        recommendations = []
        
        # Check for failed required services
        failed_services = [
            svc for svc_id, svc in self.check_results['services'].items()
            if svc['required'] and svc['status'] != 'success'
        ]
        
        if failed_services:
            recommendations.append(
                f"Fix {len(failed_services)} critical service issues before running ETL pipeline"
            )
        
        # Check for missing models
        ollama_service = self.check_results['services'].get('ollama', {})
        if ollama_service.get('status') == 'failed':
            missing_models = ollama_service.get('details', {}).get('missing_models', [])
            if missing_models:
                recommendations.append(
                    f"Install missing Ollama models: {', '.join(missing_models)}"
                )
        
        # Check for missing packages
        packages_dep = self.check_results['dependencies'].get('python_packages', {})
        if packages_dep.get('status') == 'failed':
            missing_packages = packages_dep.get('details', {}).get('missing_packages', [])
            if missing_packages:
                recommendations.append(
                    f"Install missing Python packages: pip install {' '.join(missing_packages)}"
                )
        
        # Check disk space
        disk_dep = self.check_results['dependencies'].get('disk_space', {})
        if disk_dep.get('status') == 'failed':
            recommendations.append(
                "Free up disk space before running large ETL jobs"
            )
        
        # Docker recommendations
        docker_service = self.check_results['services'].get('docker', {})
        if docker_service.get('status') == 'failed':
            missing_services = docker_service.get('details', {}).get('missing_important', [])
            if missing_services:
                recommendations.append(
                    f"Start missing Docker services: docker-compose up -d {' '.join(missing_services)}"
                )
        
        # Performance recommendations
        if len(recommendations) == 0:
            recommendations.append("All health checks passed - ETL pipeline is ready for execution")
            recommendations.append("Consider running test_etl_pipeline.py to validate end-to-end functionality")
        
        self.check_results['recommendations'] = recommendations
    
    def print_health_report(self):
        """Print comprehensive health report"""
        print(f"\n{'='*80}")
        print(f"🏥 ETL PIPELINE HEALTH REPORT")
        print(f"{'='*80}")
        
        # Overall status
        status_icon = "✅" if self.check_results['overall_status'] == 'healthy' else "❌"
        print(f"\n{status_icon} OVERALL STATUS: {self.check_results['overall_status'].upper()}")
        print(f"📅 Timestamp: {self.check_results['timestamp']}")
        
        # Services summary
        print(f"\n📋 SERVICES SUMMARY:")
        for svc_id, svc in self.check_results['services'].items():
            status_icon = "✅" if svc['status'] == 'success' else "❌" if svc['status'] == 'failed' else "⚠️"
            required_text = " (Required)" if svc['required'] else " (Optional)"
            print(f"   {status_icon} {svc['name']}{required_text}: {svc['message']}")
        
        # Dependencies summary
        print(f"\n🔧 DEPENDENCIES SUMMARY:")
        for dep_id, dep in self.check_results['dependencies'].items():
            status_icon = "✅" if dep['status'] == 'success' else "❌" if dep['status'] == 'failed' else "⚠️"
            required_text = " (Required)" if dep['required'] else " (Optional)"
            print(f"   {status_icon} {dep['name']}{required_text}: {dep['message']}")
        
        # Recommendations
        if self.check_results['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.check_results['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        # Errors summary
        if self.check_results['errors']:
            print(f"\n❌ ERRORS SUMMARY:")
            for error in self.check_results['errors']:
                print(f"   • {error}")
        
        print(f"\n{'='*80}")
    
    def save_report(self, filename: str = None):
        """Save health report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"etl_health_report_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.check_results, f, indent=2, default=str)
            self.log(f"Health report saved to {filename}", "SUCCESS")
        except Exception as e:
            self.log(f"Failed to save report: {e}", "ERROR")


async def main():
    """Main health check execution"""
    parser = argparse.ArgumentParser(description="ETL Pipeline Health Checker")
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--save-report', '-s', action='store_true',
                       help='Save health report to JSON file')
    parser.add_argument('--services-only', action='store_true',
                       help='Check only services (skip dependencies)')
    parser.add_argument('--deps-only', action='store_true',
                       help='Check only dependencies (skip services)')
    parser.add_argument('--quick', action='store_true',
                       help='Quick check (essential services only)')
    
    args = parser.parse_args()
    
    # Initialize health checker
    checker = ETLHealthChecker(verbose=args.verbose)
    
    try:
        # Run health checks
        if args.quick:
            # Override services to check only essential ones
            checker.services = {k: v for k, v in checker.services.items() 
                              if k in ['database', 'ollama']}
            checker.dependencies = {k: v for k, v in checker.dependencies.items() 
                                  if k in ['environment_variables', 'python_packages']}
        
        if args.services_only:
            checker.dependencies = {}
        elif args.deps_only:
            checker.services = {}
        
        success = await checker.run_health_checks()
        
        # Print report
        checker.print_health_report()
        
        # Save report if requested
        if args.save_report:
            checker.save_report()
        
        # Exit with appropriate code
        if success:
            print("\n🎉 All health checks passed - ETL pipeline is ready!")
            sys.exit(0)
        else:
            print("\n⚠️  Some health checks failed - review issues before running ETL pipeline")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Health check failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())