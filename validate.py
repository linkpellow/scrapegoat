#!/usr/bin/env python3
"""
Validation script for Scraper Platform Control Plane
Ensures all components are properly configured and functioning
"""

import sys
import asyncio
from typing import List, Tuple


def print_status(check_name: str, passed: bool, message: str = ""):
    """Print formatted status message"""
    status = "✅" if passed else "❌"
    print(f"{status} {check_name}")
    if message:
        print(f"   {message}")


async def check_imports() -> Tuple[bool, str]:
    """Verify all required modules can be imported"""
    try:
        import fastapi
        import pydantic
        import sqlalchemy
        import httpx
        import redis
        import celery
        import alembic
        return True, "All required packages installed"
    except ImportError as e:
        return False, f"Missing package: {e.name}"


async def check_config() -> Tuple[bool, str]:
    """Verify configuration loads correctly"""
    try:
        from app.config import settings
        return True, f"Environment: {settings.environment}"
    except Exception as e:
        return False, f"Config error: {str(e)}"


async def check_database_connection() -> Tuple[bool, str]:
    """Verify database connection"""
    try:
        from app.database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database error: {str(e)}"


async def check_models() -> Tuple[bool, str]:
    """Verify models are properly defined"""
    try:
        from app.models.job import Job
        from app.database import Base
        
        if Job.__tablename__ != "jobs":
            return False, "Job model table name incorrect"
        
        return True, "Models loaded successfully"
    except Exception as e:
        return False, f"Model error: {str(e)}"


async def check_schemas() -> Tuple[bool, str]:
    """Verify Pydantic schemas"""
    try:
        from app.schemas.job import JobCreate, JobRead
        from app.enums import ExecutionStrategy
        
        # Test schema validation
        test_job = JobCreate(
            target_url="https://example.com",
            fields=["test"],
            strategy=ExecutionStrategy.AUTO
        )
        
        return True, "Schemas validated successfully"
    except Exception as e:
        return False, f"Schema error: {str(e)}"


async def check_api() -> Tuple[bool, str]:
    """Verify API endpoints are defined"""
    try:
        from app.main import app
        
        routes = [route.path for route in app.routes]
        
        if "/jobs" not in routes:
            return False, "Jobs endpoint not found"
        
        return True, f"API configured with {len(routes)} routes"
    except Exception as e:
        return False, f"API error: {str(e)}"


async def check_validator() -> Tuple[bool, str]:
    """Verify validation logic"""
    try:
        from app.services.validator import JobValidator
        
        # Test duplicate field detection
        try:
            JobValidator.validate_fields(["field1", "field1"])
            return False, "Duplicate field validation failed"
        except ValueError:
            pass  # Expected
        
        JobValidator.validate_fields(["field1", "field2"])
        
        return True, "Validation logic working"
    except Exception as e:
        return False, f"Validator error: {str(e)}"


async def main():
    """Run all validation checks"""
    print("\n🔍 Validating Scraper Platform Control Plane\n")
    
    checks = [
        ("Package Dependencies", check_imports),
        ("Configuration", check_config),
        ("Database Connection", check_database_connection),
        ("Data Models", check_models),
        ("Pydantic Schemas", check_schemas),
        ("API Endpoints", check_api),
        ("Validation Logic", check_validator),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            passed, message = await check_func()
            print_status(check_name, passed, message)
            results.append(passed)
        except Exception as e:
            print_status(check_name, False, f"Unexpected error: {str(e)}")
            results.append(False)
    
    print("\n" + "="*50)
    passed_count = sum(results)
    total_count = len(results)
    
    if all(results):
        print(f"✅ All checks passed ({passed_count}/{total_count})")
        print("\n🚀 Control Plane is ready!")
        print("\nNext steps:")
        print("  1. Start the server: make start")
        print("  2. View API docs: http://localhost:8000/docs")
        print("  3. Create a job: curl -X POST http://localhost:8000/jobs ...")
        return 0
    else:
        print(f"❌ Some checks failed ({passed_count}/{total_count} passed)")
        print("\n💡 Troubleshooting:")
        print("  1. Ensure Docker containers are running: docker-compose ps")
        print("  2. Check database migrations: alembic current")
        print("  3. Verify .env file exists with correct values")
        print("  4. Reinstall dependencies: pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
