#!/usr/bin/env python3
"""
Test runner for the FastAPI backend test suite
"""

import sys
import os
import subprocess
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))


def run_tests(test_type="all", verbose=False, coverage=False):
    """Run the test suite"""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    test_dir = Path(__file__).parent
    
    if test_type == "unit":
        cmd.append(str(test_dir / "unit"))
    elif test_type == "integration":
        cmd.append(str(test_dir / "integration"))
    elif test_type == "api":
        cmd.append(str(test_dir / "api"))
    elif test_type == "auth":
        cmd.extend(["-m", "auth"])
    elif test_type == "admin":
        cmd.extend(["-m", "admin"])
    else:
        cmd.append(str(test_dir))
    
    # Add verbosity
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    if coverage:
        cmd.extend(["--cov=backend/app", "--cov-report=html", "--cov-report=term"])
    
    # Add other useful options
    cmd.extend([
        "--tb=short",
        "--strict-markers"
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    
    # Set environment variables for testing
    env = os.environ.copy()
    env.update({
        "TESTING": "true",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "hauntbro_test",
        "DB_USER": "test_user",
        "DB_PASSWORD": "test_password",
        "JWT_SECRET_KEY": "test_secret_key_for_testing_only",
        "JWT_ALGORITHM": "HS256",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30"
    })
    
    # Run tests
    try:
        result = subprocess.run(cmd, env=env, cwd=project_root)
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run FastAPI backend tests")
    parser.add_argument(
        "--type", 
        choices=["all", "unit", "integration", "api", "auth", "admin"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run with coverage analysis"
    )
    
    args = parser.parse_args()
    
    print("🧪 FastAPI Backend Test Suite")
    print("=" * 50)
    print(f"Test Type: {args.type}")
    print(f"Verbose: {args.verbose}")
    print(f"Coverage: {args.coverage}")
    print("=" * 50)
    
    return_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage
    )
    
    if return_code == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n❌ Tests failed with return code {return_code}")
    
    return return_code


if __name__ == "__main__":
    sys.exit(main())