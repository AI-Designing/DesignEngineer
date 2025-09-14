# Test Suite for FreeCAD LLM Automation

This directory contains comprehensive tests for the FreeCAD LLM automation system, including unified LLM management and complex model generation capabilities.

## Test Categories

### Core System Tests

- `test_imports.py` - Validates all module imports and dependencies
- `test_freecad.py` - FreeCAD API integration tests
- `test_llm.py` - LLM provider tests
- `test_redis.py` - Redis state management tests

### Advanced Feature Tests

- `test_complex_models.py` - Complex 3D model generation validation
- `test_improved_prompting_system.py` - Enhanced DeepSeek R1 prompting tests
- `test_cylinder_validation.py` - Basic geometry validation tests
- `test_gear_generation.py` - Complex gear generation tests

### Integration Tests

- `test_integration.py` - End-to-end system integration
- `test_enhanced_system.py` - Enhanced system capabilities
- `test_phase3_integration.py` - Advanced workflow integration

### Workflow Tests

- `test_phase3_workflow.py` - Complex workflow validation
- `test_state_analysis.py` - State management tests
- `test_sketch_then_operate.py` - Sketch-based operations

## Running Tests

### Prerequisites

Ensure the following services are running:
- Redis server (port 6379)
- Ollama with DeepSeek R1 model (port 11434)
- FreeCAD available in system PATH

### Basic Test Execution

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/test_complex_models.py -v
python -m pytest tests/test_improved_prompting_system.py -v

# Run with virtual environment
source venv/bin/activate
python -m pytest tests/ -v
```

### Individual Test Execution

```bash
# Test imports and dependencies
python tests/test_imports.py

# Test complex model generation
python tests/test_complex_models.py

# Test improved prompting system
python tests/test_improved_prompting_system.py

# Test specific geometry validation
python tests/test_cylinder_validation.py
```

## Test Configuration

### Environment Variables

Set these environment variables for testing:
```bash
export GOOGLE_API_KEY="your_api_key"  # Optional for Gemini tests
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export OLLAMA_HOST="localhost:11434"
```

### Test Modes

Tests support different execution modes:
- `headless=True` - For automated testing without GUI
- `enable_websocket=False` - Disable WebSocket for faster tests
- `enable_persistent_gui=False` - Disable GUI persistence

## Test Results

Tests generate output files in the `outputs/` directory:
- `*.FCStd` - Generated FreeCAD models
- `test_report_*.json` - Detailed test results
- `performance_metrics.json` - Performance analysis

## Validation Criteria

### Basic Geometry Tests
- ✅ File size > 1500 bytes (contains actual geometry)
- ✅ Valid FreeCAD Shape objects
- ✅ Correct volume calculations
- ✅ Expected face counts per shape type

### Complex Model Tests
- ✅ Multiple object creation
- ✅ Boolean operations validation
- ✅ Advanced geometry features
- ✅ Performance within acceptable limits

### LLM Integration Tests
- ✅ Provider switching functionality
- ✅ Response quality and confidence scores
- ✅ Error handling and fallback mechanisms
- ✅ Prompt optimization effectiveness

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Redis Connection**: Verify Redis server is running
3. **FreeCAD Path**: Check FreeCAD installation and PATH
4. **Ollama Model**: Ensure DeepSeek R1 model is downloaded

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Issues

For slow tests, check:
- Ollama model loading time
- Redis connection latency
- FreeCAD initialization overhead

## Contributing

When adding new tests:
1. Follow the naming convention `test_*.py`
2. Include docstrings explaining test purpose
3. Add validation criteria and expected outcomes
4. Update this README with new test descriptions

## Recent Improvements

### DeepSeek R1 Prompting Enhancements
- ✅ Complexity-aware prompt selection
- ✅ FreeCAD API pattern guidance
- ✅ Error prevention through better examples
- ✅ Shape-specific validation logic

### Test Infrastructure
- ✅ Organized test structure
- ✅ Comprehensive validation criteria
- ✅ Performance monitoring
- ✅ Error tracking and reporting
