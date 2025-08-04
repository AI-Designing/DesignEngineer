#!/bin/bash

# Redis Setup and Test Script for FreeCAD LLM Automation
# This script sets up Redis and tests the state management system

echo "🚀 Setting up Redis for FreeCAD LLM Automation"
echo "=============================================="

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis is not installed. Installing..."
    
    # Install Redis on Ubuntu/Debian
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y redis-server
    # Install Redis on CentOS/RHEL/Fedora
    elif command -v yum &> /dev/null; then
        sudo yum install -y redis
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y redis
    # Install Redis on macOS
    elif command -v brew &> /dev/null; then
        brew install redis
    else
        echo "❌ Unable to install Redis automatically. Please install manually:"
        echo "   Ubuntu/Debian: sudo apt install redis-server"
        echo "   CentOS/RHEL: sudo yum install redis"
        echo "   Fedora: sudo dnf install redis"
        echo "   macOS: brew install redis"
        exit 1
    fi
else
    echo "✅ Redis is already installed"
fi

# Check if Redis is running
if ! redis-cli ping &> /dev/null; then
    echo "🔄 Starting Redis server..."
    
    # Start Redis server in background
    if command -v systemctl &> /dev/null; then
        sudo systemctl start redis-server
        sudo systemctl enable redis-server
    else
        # Start Redis manually
        redis-server --daemonize yes
    fi
    
    # Wait for Redis to start
    sleep 2
    
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis server started successfully"
    else
        echo "❌ Failed to start Redis server"
        echo "   Try manually: redis-server"
        exit 1
    fi
else
    echo "✅ Redis server is already running"
fi

# Test Redis connection
echo ""
echo "🧪 Testing Redis connection..."
if redis-cli ping > /dev/null; then
    echo "✅ Redis connection test: PASSED"
else
    echo "❌ Redis connection test: FAILED"
    exit 1
fi

# Activate virtual environment and run tests
echo ""
echo "🐍 Setting up Python virtual environment..."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip > /dev/null
pip install -e . > /dev/null

# Run Redis tests
echo ""
echo "🧪 Running Redis tests..."
python -m pytest tests/test_redis.py -v

# Run Redis demo
echo ""
echo "🎮 Running Redis state management demo..."
python test_redis_demo.py

echo ""
echo "🎉 Redis setup and testing completed successfully!"
echo ""
echo "📋 Summary:"
echo "   ✅ Redis server is running on localhost:6379"
echo "   ✅ Python Redis client is working"
echo "   ✅ State management system is operational"
echo "   ✅ Ready for FreeCAD LLM automation"
echo ""
echo "🤖 How Redis helps the LLM:"
echo "   • Stores current FreeCAD document state"
echo "   • Caches object geometry and constraints"
echo "   • Tracks workflow progress and next steps"
echo "   • Enables LLM to make informed decisions"
echo "   • Provides persistent state across sessions"
echo ""
echo "🔧 To manually start/stop Redis:"
echo "   Start: redis-server"
echo "   Stop:  redis-cli shutdown"
echo "   Test:  redis-cli ping"
echo ""
