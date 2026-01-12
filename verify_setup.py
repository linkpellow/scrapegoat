#!/usr/bin/env python3
"""
Comprehensive setup verification script
Checks all dependencies and services before starting the servers
"""
import sys
import os
from pathlib import Path


def check_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check_item(name, status, message=""):
    symbol = "✅" if status else "❌"
    print(f"{symbol} {name:<40} {message}")
    return status


def main():
    print("\n🔍 SCRAPER PLATFORM - SETUP VERIFICATION")
    print("="*60)
    
    all_checks_passed = True
    
    # 1. Check Environment
    check_section("1. ENVIRONMENT")
    
    # Check Python version
    py_version = sys.version_info
    py_ok = py_version >= (3, 8)
    all_checks_passed &= check_item(
        "Python Version",
        py_ok,
        f"v{py_version.major}.{py_version.minor}.{py_version.micro}"
    )
    
    # Check virtual environment
    venv_ok = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    all_checks_passed &= check_item(
        "Virtual Environment Active",
        venv_ok,
        "Active" if venv_ok else "Not active (run: source venv/bin/activate)"
    )
    
    # 2. Check Core Dependencies
    check_section("2. PYTHON DEPENDENCIES")
    
    deps = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("sqlalchemy", "SQLAlchemy"),
        ("alembic", "Alembic"),
        ("celery", "Celery"),
        ("redis", "Redis Client"),
        ("playwright", "Playwright"),
        ("scrapy", "Scrapy"),
        ("psycopg", "psycopg"),
    ]
    
    for module, name in deps:
        try:
            __import__(module)
            all_checks_passed &= check_item(name, True, "Installed")
        except ImportError:
            all_checks_passed &= check_item(name, False, "Missing")
    
    # 3. Check Configuration Files
    check_section("3. CONFIGURATION FILES")
    
    config_files = [
        (".env", "Backend Environment"),
        ("web/.env.local", "Frontend Environment"),
        ("requirements.txt", "Python Requirements"),
        ("web/package.json", "Node.js Package Config"),
        ("alembic.ini", "Alembic Config"),
    ]
    
    for filepath, name in config_files:
        exists = Path(filepath).exists()
        all_checks_passed &= check_item(name, exists, "Found" if exists else "Missing")
    
    # 4. Check Docker Services
    check_section("4. DOCKER SERVICES")
    
    import subprocess
    
    def check_docker_service(container_name, service_name):
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            running = "Up" in result.stdout
            return check_item(service_name, running, "Running" if running else "Not running")
        except Exception as e:
            return check_item(service_name, False, f"Error: {e}")
    
    all_checks_passed &= check_docker_service("postgres", "PostgreSQL")
    all_checks_passed &= check_docker_service("redis", "Redis")
    
    # 5. Check Database Connection
    check_section("5. DATABASE CONNECTION")
    
    try:
        from app.database import engine
        with engine.connect() as conn:
            all_checks_passed &= check_item("PostgreSQL Connection", True, "Connected")
            
            # Check tables
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            expected_tables = {'jobs', 'runs', 'run_events', 'field_maps', 'records', 'session_vaults', 'alembic_version'}
            tables_ok = expected_tables.issubset(set(tables))
            all_checks_passed &= check_item(
                "Database Tables",
                tables_ok,
                f"{len(tables)} tables found"
            )
    except Exception as e:
        all_checks_passed &= check_item("PostgreSQL Connection", False, f"Error: {str(e)[:40]}")
    
    # 6. Check Redis Connection
    check_section("6. REDIS CONNECTION")
    
    try:
        import redis
        r = redis.from_url("redis://localhost:6379/0")
        r.ping()
        all_checks_passed &= check_item("Redis Connection", True, "Connected")
    except Exception as e:
        all_checks_passed &= check_item("Redis Connection", False, f"Error: {str(e)[:40]}")
    
    # 7. Check Application Imports
    check_section("7. APPLICATION IMPORTS")
    
    try:
        from app.main import app
        all_checks_passed &= check_item("FastAPI App", True, "Imports successfully")
    except Exception as e:
        all_checks_passed &= check_item("FastAPI App", False, f"Error: {str(e)[:40]}")
    
    try:
        from app.celery_app import celery_app
        all_checks_passed &= check_item("Celery App", True, "Imports successfully")
    except Exception as e:
        all_checks_passed &= check_item("Celery App", False, f"Error: {str(e)[:40]}")
    
    # 8. Check Playwright
    check_section("8. PLAYWRIGHT BROWSERS")
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # This will fail if chromium is not installed
            browser = p.chromium.launch(headless=True)
            browser.close()
            all_checks_passed &= check_item("Chromium Browser", True, "Installed")
    except Exception as e:
        all_checks_passed &= check_item("Chromium Browser", False, "Not installed (run: python -m playwright install chromium)")
    
    # 9. Check Node.js Dependencies
    check_section("9. FRONTEND DEPENDENCIES")
    
    node_modules_ok = Path("web/node_modules").exists()
    all_checks_passed &= check_item(
        "Node Modules",
        node_modules_ok,
        "Installed" if node_modules_ok else "Missing (run: cd web && npm install)"
    )
    
    # Final Summary
    print("\n" + "="*60)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - SYSTEM READY!")
        print("="*60)
        print("\nYou can now start the servers:")
        print("\n  Terminal 1: make start")
        print("  Terminal 2: make start-worker")
        print("  Terminal 3: make start-web")
        print("\nOr read START_SERVERS.md for detailed instructions.\n")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - PLEASE FIX ISSUES ABOVE")
        print("="*60)
        print("\nRefer to SETUP_COMPLETE.md for troubleshooting.\n")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
