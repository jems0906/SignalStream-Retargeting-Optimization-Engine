#!/usr/bin/env python3
"""
Startup script for Real-Time Retargeting & Optimization Signals Service
"""

import os
import sys
import subprocess
import time
import requests
import argparse
from pathlib import Path

# Add src to path for importing config
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.config import config
    from src.logging_config import setup_logging
except ImportError as e:
    print(f"Error importing configuration: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def check_redis_connection(host: str = None, port: int = None) -> bool:
    """Check if Redis is running and accessible"""
    host = host or config.redis.host
    port = port or config.redis.port
    
    try:
        import redis
        r = redis.Redis(host=host, port=port, db=config.redis.db)
        r.ping()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False


def start_redis():
    """Start Redis using Docker Compose"""
    print("Starting Redis...")
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d", "redis"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            print("✓ Redis started successfully")
            # Wait for Redis to be ready
            time.sleep(3)
            return True
        else:
            print(f"Failed to start Redis: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error starting Redis: {e}")
        return False


def install_dependencies():
    """Install Python dependencies"""
    print("Installing dependencies...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Dependencies installed successfully")
            return True
        else:
            print(f"Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return False


def start_api_server(host: str = None, port: int = None, reload: bool = None):
    """Start the FastAPI server"""
    host = host or config.server.host
    port = port or config.server.port
    reload = reload if reload is not None else config.server.reload
    
    print(f"Starting API server on {host}:{port}...")
    try:
        # Start server in background
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "src.main:app", 
            "--host", host, 
            "--port", str(port),
            "--log-level", config.server.log_level.lower()
        ] + (["--reload"] if reload else []))
        
        # Wait for server to start
        time.sleep(5)
        
        # Check if server is running
        server_url = f"http://{host}:{port}"
        try:
            response = requests.get(server_url, timeout=10)
            if response.status_code == 200:
                print("✓ API server started successfully")
                print(f"  📡 API available at: {server_url}")
                print(f"  📚 Docs available at: {server_url}/docs")
                return process
            else:
                print("❌ API server not responding properly")
                return None
        except requests.RequestException as e:
            print(f"❌ API server not accessible: {e}")
            return None
            
    except Exception as e:
        print(f"Error starting API server: {e}")
        return None


def run_demo(server_url: str = None):
    """Run a quick demo"""
    if not server_url:
        server_url = f"http://{config.server.host}:{config.server.port}"
        
    print("\nRunning demo...")
    
    try:
        # Generate demo events
        print("1. Generating demo events...")
        response = requests.post(f"{server_url}/v1/demo/generate-events?count=20", timeout=10)
        if response.status_code == 200:
            print("   ✓ Generated 20 demo events")
        
        # Simulate user journey
        print("2. Simulating user journey...")
        response = requests.post(f"{server_url}/v1/demo/user-journey", timeout=10)
        if response.status_code == 200:
            data = response.json()
            user_id = data.get('user_id')
            print(f"   ✓ Simulated journey for user {user_id}")
        
        # Check audiences
        print("3. Checking audiences...")
        response = requests.get(f"{server_url}/v1/audiences", timeout=10)
        if response.status_code == 200:
            data = response.json()
            for audience_id, info in data.items():
                member_count = info.get('member_count', 0)
                print(f"   • {info['name']}: {member_count} members")
        
        print("\n🎉 Demo completed successfully!")
        print(f"\nNext steps:")
        print(f"• Visit {server_url}/docs for full API documentation")
        print("• Use Postman or curl to test the APIs")
        print("• Check user profiles: GET /v1/users/{user_id}/profile")
        print("• Monitor audiences: GET /v1/audiences/{audience_id}/members")
        
    except Exception as e:
        print(f"Demo failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Start the Retargeting Service")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-redis", action="store_true", help="Skip Redis startup")
    parser.add_argument("--demo", action="store_true", help="Run demo after startup")
    parser.add_argument("--host", type=str, help="Override server host")
    parser.add_argument("--port", type=int, help="Override server port")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(config.server.log_level)
    
    print(f"🚀 {config.service_name} v{config.version}")
    print("=" * 60)
    
    # Install dependencies
    if not args.skip_deps:
        if not install_dependencies():
            print("❌ Dependency installation failed")
            return 1
    
    # Start Redis
    if not args.skip_redis:
        if not check_redis_connection():
            if not start_redis():
                print("❌ Failed to start Redis")
                print("💡 Try running: docker-compose up -d redis")
                return 1
    
    # Verify Redis connection
    if not check_redis_connection():
        print("⚠️  Redis is not accessible")
        print(f"💡 Make sure Redis is running on {config.redis.host}:{config.redis.port}")
        print("   Service will use in-memory storage as fallback")
    else:
        print(f"✓ Redis is running and accessible at {config.redis.host}:{config.redis.port}")
    
    # Start API server
    server_process = start_api_server(args.host, args.port)
    if not server_process:
        print("❌ Failed to start API server")
        return 1
    
    # Run demo if requested
    if args.demo:
        time.sleep(2)  # Give server time to fully start
        server_url = f"http://{args.host or config.server.host}:{args.port or config.server.port}"
        run_demo(server_url)
    
    server_url = f"http://{args.host or config.server.host}:{args.port or config.server.port}"
    print("\n" + "=" * 60)
    print("🎯 Service is running!")
    print(f"   API: {server_url}")
    print(f"   Docs: {server_url}/docs")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Keep the script running
        server_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        server_process.terminate()
        print("✓ Service stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())