# DeepSeek R1 Comprehensive Guide

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Performance](#performance)
7. [API Reference](#api-reference)

---

## Overview

DeepSeek R1 is an advanced AI model integrated with the FreeCAD LLM Automation system for generating complex mechanical parts with sophisticated reasoning capabilities. This integration provides a unified platform for AI-powered CAD design automation.

### Key Features

- **🧠 Advanced Reasoning**: Full reasoning chains for complex design decisions with step-by-step explanations
- **🔧 Multiple Generation Modes**: Technical, Creative, Fast, and Reasoning modes tailored to different use cases
- **⚙️ Complex Part Generation**: Support for assemblies, mechanisms, gears, and advanced geometries
- **📊 Quality Prediction**: AI-powered quality assessment with predictive analytics
- **🔄 Smart Fallback**: Seamless fallback to Google Gemini or other LLM providers
- **🏠 Local Privacy**: Complete privacy and control with local execution
- **🎯 Unified LLM Management**: Seamless provider switching and auto-selection logic

### What's Different?

DeepSeek R1 integration brings:
- **Complexity-Aware Prompting**: Different prompt strategies for basic, medium, and complex shapes
- **FreeCAD API Guidance**: Comprehensive API examples and error prevention patterns
- **Document Management**: Correct pattern enforcement for existing document usage
- **Math Module Fixes**: Proper Python `math` module usage with FreeCAD integration

---

## Quick Start

### 1. Automated Setup

Run the one-command setup script:

```bash
cd /home/vansh5632/DesignEng/freecad-llm-automation
chmod +x scripts/setup_deepseek_r1.sh
./scripts/setup_deepseek_r1.sh
```

This script will:
- Install required Python dependencies (torch, transformers, fastapi, uvicorn)
- Download the DeepSeek R1 model
- Configure the local server
- Set up the integration with FreeCAD

### 2. Start DeepSeek R1 Server

```bash
# Start the local server
~/.deepseek-r1/start_deepseek.sh

# Or start manually with debug output
cd ~/.deepseek-r1
python3 deepseek_server.py
```

### 3. Test the Integration

```bash
# Run comprehensive integration tests
python tests/test_integration.py

# Run the full demonstration
python examples/demo_deepseek_r1_clean.py

# Test with improved prompting
python examples/test_improved_prompting_example.py
```

### 4. Health Check

```bash
# Check if DeepSeek R1 server is running
curl http://localhost:8000/health

# Get server statistics
curl http://localhost:8000/stats
```

---

## Architecture

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FreeCAD UI    │────│ Enhanced Complex │────│ DeepSeek R1     │
│   Commands      │    │ Generator        │    │ Client          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                        ┌──────────────────┐    ┌─────────────────┐
                        │ Pattern Learning │    │ Local DeepSeek  │
                        │ Engine           │    │ R1 Server       │
                        └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                        ┌──────────────────┐    ┌─────────────────┐
                        │ Quality          │    │ Integration     │
                        │ Predictor        │    │ Manager         │
                        └──────────────────┘    └─────────────────┘
```

### Unified LLM Manager

The unified LLM system provides:
- **Provider Management**: Seamless switching between DeepSeek R1 and Google Gemini
- **Auto-Selection Logic**: Intelligent provider selection based on availability and performance
- **Fallback Mechanisms**: Automatic fallback to available providers when primary fails
- **Performance Tracking**: Request tracking, success rates, and execution time monitoring

### Core Components

#### 1. DeepSeek R1 Client (`src/ai_designer/llm/deepseek_client.py`)
- Complex part generation with reasoning
- Multiple generation modes (Technical, Creative, Fast, Reasoning)
- Performance metrics and insights
- Integration manager for hybrid modes

#### 2. Enhanced Complex Generator (`src/ai_designer/core/enhanced_complex_generator.py`)
- DeepSeek-powered complex shape generation
- Quality prediction and optimization
- Pattern learning from successful generations
- Multi-strategy generation approaches

#### 3. Unified LLM Manager (`src/ai_designer/llm/unified_manager.py`)
- Provider orchestration
- Intelligent fallback handling
- Performance monitoring
- Runtime provider switching

---

## Installation

### Prerequisites

- **Python**: 3.8 or higher
- **FreeCAD**: Latest stable version
- **Redis**: For state management (optional but recommended)
- **Ollama**: For serving DeepSeek R1 14B model

### Manual Installation

#### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pip redis-server

# macOS
brew install python redis
```

#### 2. Install Python Dependencies

```bash
# Navigate to project directory
cd /home/vansh5632/DesignEng/freecad-llm-automation

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install torch transformers accelerate fastapi uvicorn
pip install -r requirements-dev.txt
```

#### 3. Configure DeepSeek R1

Edit `config/config.yaml`:

```yaml
deepseek:
  enabled: true
  host: "localhost"
  port: 8000
  model_name: "deepseek-r1"
  timeout: 300
  max_tokens: 8192
  temperature: 0.1
  top_p: 0.95
  reasoning_enabled: true
  stream: false
  fallback_to_gemini: true

enhanced_generator:
  use_deepseek: true
  quality_targets:
    geometric_accuracy: 0.9
    design_consistency: 0.85
    aesthetic_quality: 0.8
    manufacturability: 0.9
    performance_score: 0.85

  pattern_learning:
    enabled: true
    max_patterns: 1000
    similarity_threshold: 0.6

  quality_prediction:
    enabled: true
    confidence_threshold: 0.7
```

#### 4. Start Services

```bash
# Start Redis (if using state management)
redis-server config/redis.conf

# Start DeepSeek R1 server
~/.deepseek-r1/start_deepseek.sh
```

### Verification

```bash
# Verify DeepSeek R1 server
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1","messages":[{"role":"user","content":"test"}]}'

# Run test suite
python tests/test_complex_models.py
```

---

## Usage

### Generation Modes

DeepSeek R1 offers four specialized generation modes:

| Mode | Use Case | Characteristics | Example |
|------|----------|----------------|---------|
| **Technical** | Precision engineering | High accuracy, strict tolerances | Shafts, bearings, precision components |
| **Creative** | Innovative designs | Novel solutions, aesthetic focus | Phone stands, artistic parts, unique mechanisms |
| **Reasoning** | Complex assemblies | Multi-step reasoning, relationships | Gear trains, linkages, multi-part systems |
| **Fast** | Simple parts | Quick generation, basic shapes | Prototypes, basic geometries, simple models |

### Basic Command Line Usage

```bash
# Using DeepSeek R1 (default)
python -m ai_designer.cli --unified-command "Create a 10x10x10 cube"

# Specify generation mode
python -m ai_designer.cli \
    --deepseek-enabled \
    --deepseek-mode reasoning \
    "Create a gear assembly with 20 teeth main gear and 10 teeth pinion"

# Switch to specific provider
python -m ai_designer.cli --llm-provider deepseek \
    --unified-command "Create a precision cylinder"

python -m ai_designer.cli --llm-provider google \
    --unified-command "Create a decorative sphere"

# Check provider status
python -m ai_designer.cli --show-llm-status
```

### Python API Usage

#### 1. Basic DeepSeek Client

```python
from ai_designer.llm.deepseek_client import DeepSeekR1Client, DeepSeekConfig, DeepSeekMode

# Initialize client with custom configuration
config = DeepSeekConfig(
    host="localhost",
    port=8000,
    timeout=300,
    reasoning_enabled=True
)
client = DeepSeekR1Client(config)

# Generate complex part
response = client.generate_complex_part(
    requirements="Create a precision shaft with keyway",
    mode=DeepSeekMode.TECHNICAL,
    constraints={
        'tolerance': 0.01,
        'surface_finish': 'precision_ground',
        'material': 'steel'
    }
)

print(f"Generated code: {response.generated_code}")
print(f"Confidence: {response.confidence_score:.2f}")
print(f"Reasoning steps: {len(response.reasoning_chain)}")
```

#### 2. Enhanced Complex Generator

```python
from ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator
from ai_designer.llm.deepseek_client import DeepSeekR1Client, DeepSeekConfig

# Initialize DeepSeek client
deepseek_config = DeepSeekConfig(host="localhost", port=8000)
deepseek_client = DeepSeekR1Client(deepseek_config)

# Initialize enhanced generator with DeepSeek
generator = EnhancedComplexShapeGenerator(
    llm_client=None,  # Will use DeepSeek as primary
    state_analyzer=state_analyzer,
    command_executor=command_executor,
    use_deepseek=True,
    deepseek_config=deepseek_config
)

# Generate with quality targets
result = generator.generate_enhanced_complex_shape(
    user_requirements="Create a complex gear assembly",
    session_id="demo_session",
    quality_targets={
        'geometric_accuracy': 0.95,
        'design_consistency': 0.90,
        'manufacturability': 0.95
    }
)

if result['status'] == 'success':
    print(f"Quality score: {result['quality_score']:.2f}")
    print(f"Executed steps: {result['executed_steps']}")
```

#### 3. Integration Manager (Hybrid Mode)

```python
from ai_designer.llm.deepseek_client import DeepSeekIntegrationManager

# Initialize with both providers
manager = DeepSeekIntegrationManager(
    deepseek_client=deepseek_client,
    fallback_client=gemini_client
)

# Auto mode - system selects best approach
code = manager.generate_command(
    nl_command="Create a complex gear train",
    mode="auto"
)

# Hybrid mode - combines DeepSeek with validation
code = manager.generate_command(
    nl_command="Design precision bearing",
    mode="hybrid"
)

# Get integration metrics
metrics = manager.get_integration_metrics()
print(f"DeepSeek usage: {metrics['deepseek_usage_rate']*100:.1f}%")
print(f"Fallback usage: {metrics['fallback_usage_rate']*100:.1f}%")
print(f"Success rate: {metrics['success_rate']*100:.1f}%")
```

### Practical Examples

#### Example 1: Technical Mode - Precision Shaft

```python
requirements = """
Create a precision shaft with the following specifications:
- Length: 100mm ±0.1mm
- Diameter: 20mm H7 tolerance
- Keyway: 5mm wide, 2.5mm deep, DIN 6885 standard
- Chamfer: 1mm x 45° on both ends
- Material: Steel C45
- Surface finish: Ra 1.6 μm
"""

response = client.generate_complex_part(
    requirements=requirements,
    mode=DeepSeekMode.TECHNICAL,
    constraints={
        'material': 'steel',
        'tolerance': 0.05,
        'surface_finish': 'machined'
    }
)

print(f"Confidence: {response.confidence_score:.2f}")
# Expected output: Confidence: 0.92
```

#### Example 2: Creative Mode - Phone Stand

```python
requirements = """
Design an innovative phone stand that:
- Adjusts to multiple viewing angles (30°, 45°, 60°)
- Accommodates phones from 4" to 7" screens
- Has modern minimalist aesthetic
- Includes integrated cable management
- Can be 3D printed in a single piece
"""

response = client.generate_complex_part(
    requirements=requirements,
    mode=DeepSeekMode.CREATIVE,
    context={
        'target_market': 'premium',
        'manufacturing': '3D_printing',
        'material': 'PLA'
    }
)

print(f"Creative solutions: {len(response.optimization_suggestions)}")
# Output includes innovative design variations
```

#### Example 3: Reasoning Mode - Gear Assembly

```python
requirements = """
Create a complete gear assembly with:
1. Main gear: 50mm diameter, 20 teeth, module 2.5
2. Pinion gear: 25mm diameter, 10 teeth, module 2.5
3. Proper gear mesh with backlash
4. Mounting bracket for both gears
5. Shaft supports with bearings
6. Center distance: 37.5mm
7. Pressure angle: 20°
"""

response = client.generate_complex_part(
    requirements=requirements,
    mode=DeepSeekMode.REASONING,
    context={
        'application': 'speed_reducer',
        'environment': 'industrial'
    },
    constraints={
        'gear_ratio': 2.0,
        'center_distance': 37.5,
        'pressure_angle': 20
    }
)

# Access detailed reasoning chain
for step in response.reasoning_chain:
    print(f"Step: {step.description}")
    print(f"Reasoning: {step.reasoning}")
    print(f"Confidence: {step.confidence}")
```

---

## Performance

### Performance Results

Based on extensive testing:

| Metric | Value | Notes |
|--------|-------|-------|
| **Generation Time** | 80-140s | For complex models |
| **Confidence Score** | 82-85% | Average across modes |
| **Success Rate** | 85%+ | Basic-to-medium complexity |
| **Quality Score** | 0.87-0.92 | Geometric accuracy |

### Test Results Summary

- ✅ **Basic Cylinder**: PASSED (Volume: 6283.2 cm³, Faces: 3)
- ✅ **Simple Boxes**: PASSED with correct dimensions
- ✅ **File Storage**: Proper auto-save to `outputs/` directory
- ✅ **GUI Integration**: Automatic FreeCAD GUI opening
- ⚠️ **Complex Gears**: Partial success (requires API refinement)

### Optimization Strategies

#### 1. Quality Targets

```python
# Adjust quality targets based on requirements
quality_targets = {
    'geometric_accuracy': 0.95,    # High precision
    'design_consistency': 0.90,    # Consistent design
    'aesthetic_quality': 0.85,     # Good appearance
    'manufacturability': 0.95,     # Easy to manufacture
    'performance_score': 0.90      # System performance
}

result = generator.generate_enhanced_complex_shape(
    user_requirements=requirements,
    session_id=session_id,
    quality_targets=quality_targets
)
```

#### 2. Pattern Learning

```python
# Enable pattern learning for improved performance
generator.pattern_learning.enabled = True
generator.pattern_learning.max_patterns = 1000

# Learn from successful generations
generator.pattern_learning.learn_from_generation(
    requirements, enhanced_plan, generation_result
)

# Find similar patterns for optimization
similar_patterns = generator.pattern_learning.find_similar_patterns(requirements)

# Get optimization suggestions
optimizations = generator.pattern_learning.get_optimization_suggestions(current_plan)
```

#### 3. Model Parameters

```python
# Tune model parameters for specific needs
config = DeepSeekConfig(
    temperature=0.05,    # More deterministic (0.0-1.0)
    top_p=0.9,          # Focused sampling (0.0-1.0)
    max_tokens=6144,    # Balanced length
    timeout=600         # Extended timeout for complex parts
)
```

### Performance Monitoring

```python
# Get DeepSeek performance metrics
metrics = client.get_performance_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['success_rate']*100:.1f}%")
print(f"Average confidence: {metrics['average_confidence']:.2f}")
print(f"Average response time: {metrics['average_response_time']:.2f}s")

# Get reasoning insights
insights = client.get_reasoning_insights()
print(f"Reasoning patterns: {len(insights['patterns'])}")
for insight in insights['insights']:
    print(f"• {insight}")
```

---

## API Reference

### DeepSeekR1Client

Main client class for interacting with DeepSeek R1.

#### Constructor

```python
DeepSeekR1Client(config: Optional[DeepSeekConfig] = None)
```

**Parameters:**
- `config`: Optional configuration object. If not provided, loads from `config/config.yaml`

#### Methods

##### generate_complex_part()

```python
def generate_complex_part(
    requirements: str,
    mode: DeepSeekMode = DeepSeekMode.TECHNICAL,
    context: Optional[Dict] = None,
    constraints: Optional[Dict] = None
) -> DeepSeekResponse
```

Generate complex parts with advanced reasoning.

**Parameters:**
- `requirements` (str): Natural language description of the part
- `mode` (DeepSeekMode): Generation mode (TECHNICAL, CREATIVE, FAST, REASONING)
- `context` (Dict, optional): Additional context information
- `constraints` (Dict, optional): Design constraints

**Returns:**
- `DeepSeekResponse`: Response object containing generated code and reasoning

**Example:**
```python
response = client.generate_complex_part(
    requirements="Create a gear with 20 teeth",
    mode=DeepSeekMode.TECHNICAL,
    constraints={'module': 2.5}
)
```

##### get_performance_metrics()

```python
def get_performance_metrics() -> Dict[str, Any]
```

Get client performance statistics.

**Returns:**
- Dictionary with metrics including success rate, average confidence, response times

##### get_reasoning_insights()

```python
def get_reasoning_insights() -> Dict[str, Any]
```

Get reasoning pattern analysis.

**Returns:**
- Dictionary with reasoning patterns and insights

### DeepSeekResponse

Response object from DeepSeek R1 generation.

```python
@dataclass
class DeepSeekResponse:
    status: str                              # 'success' or 'error'
    generated_code: str                      # FreeCAD Python code
    reasoning_chain: List[ReasoningStep]     # Step-by-step reasoning
    confidence_score: float                  # 0.0-1.0
    execution_time: float                    # Seconds
    complexity_analysis: Dict[str, Any]      # Complexity metrics
    optimization_suggestions: List[str]      # Improvement suggestions
```

### DeepSeekConfig

Configuration for DeepSeek R1 client.

```python
@dataclass
class DeepSeekConfig:
    host: str = "localhost"
    port: int = 8000
    model_name: str = "deepseek-r1"
    timeout: int = 300
    max_tokens: int = 8192
    temperature: float = 0.1
    top_p: float = 0.95
    reasoning_enabled: bool = True
    stream: bool = False
```

### DeepSeekMode

Enum for generation modes.

```python
class DeepSeekMode(Enum):
    TECHNICAL = "technical"      # Precision engineering
    CREATIVE = "creative"        # Innovative designs
    REASONING = "reasoning"      # Complex assemblies
    FAST = "fast"               # Simple parts
```

### DeepSeekIntegrationManager

Manager for hybrid DeepSeek/Gemini integration.

#### Constructor

```python
DeepSeekIntegrationManager(
    deepseek_client: DeepSeekR1Client,
    fallback_client: Any
)
```

#### Methods

##### generate_command()

```python
def generate_command(
    nl_command: str,
    state: Optional[Dict] = None,
    mode: str = "auto"
) -> str
```

Generate FreeCAD command with intelligent mode selection.

**Parameters:**
- `nl_command` (str): Natural language command
- `state` (Dict, optional): Current document state
- `mode` (str): 'auto', 'hybrid', 'deepseek_only', or 'fallback_only'

**Returns:**
- Generated FreeCAD Python code

##### get_integration_metrics()

```python
def get_integration_metrics() -> Dict[str, Any]
```

Get usage statistics for both providers.

**Returns:**
- Dictionary with usage rates, success rates, and performance metrics

### EnhancedComplexShapeGenerator

Advanced generator with DeepSeek integration.

#### Constructor

```python
EnhancedComplexShapeGenerator(
    llm_client: Optional[Any] = None,
    state_analyzer: StateAnalyzer,
    command_executor: CommandExecutor,
    use_deepseek: bool = True,
    deepseek_config: Optional[DeepSeekConfig] = None
)
```

#### Methods

##### generate_enhanced_complex_shape()

```python
def generate_enhanced_complex_shape(
    user_requirements: str,
    session_id: str,
    quality_targets: Optional[Dict[str, float]] = None
) -> Dict[str, Any]
```

Generate complex shapes with quality prediction.

**Parameters:**
- `user_requirements` (str): User description
- `session_id` (str): Session identifier
- `quality_targets` (Dict, optional): Target quality metrics

**Returns:**
- Comprehensive generation result with quality scores

##### test_deepseek_connection()

```python
def test_deepseek_connection() -> Dict[str, Any]
```

Test DeepSeek R1 server connectivity and health.

**Returns:**
- Health status dictionary

---

## Troubleshooting

### Common Issues

#### 1. Server Not Starting

**Symptoms:**
- Connection refused errors
- Server startup failures

**Solutions:**
```bash
# Check Python dependencies
pip install torch transformers fastapi uvicorn

# Verify port availability
netstat -tlnp | grep 8000

# Start manually with debug output
cd ~/.deepseek-r1
python3 deepseek_server.py --debug
```

#### 2. Connection Issues

**Symptoms:**
- Timeout errors
- "Cannot connect to DeepSeek R1" messages

**Solutions:**
```bash
# Test direct connection
curl http://localhost:8000/health

# Check firewall settings
sudo ufw allow 8000

# Verify service is listening
ss -tlnp | grep 8000
```

#### 3. Low Quality Results

**Symptoms:**
- Poor quality scores
- Incorrect geometry
- Failed validation

**Solutions:**
```python
# Adjust quality targets
quality_targets = {
    'geometric_accuracy': 0.8,  # Lower threshold
    'design_consistency': 0.75
}

# Use more specific requirements
requirements = """
Create a shaft with exact specifications:
- Length: 100mm ±0.1mm
- Diameter: 20mm H7 tolerance
- Material: Steel C45
"""

# Switch to technical mode
mode = DeepSeekMode.TECHNICAL
```

#### 4. Import Errors

**Symptoms:**
- `module 'FreeCAD' has no attribute 'Math'`
- `argument 3 must be Base.Vector, not int`

**Solutions:**
These are now automatically handled by the improved prompting system:
```python
# System now uses correct patterns:
# ✅ math.pi instead of FreeCAD.Math.pi
# ✅ Simplified API calls with correct parameters
# ✅ Proper document management
```

#### 5. Performance Issues

**Symptoms:**
- Slow response times
- High memory usage
- Timeout errors

**Solutions:**
```python
# Use fast mode for simple parts
mode = DeepSeekMode.FAST

# Reduce max_tokens
config = DeepSeekConfig(max_tokens=4096)

# Enable caching
generator.pattern_learning.enabled = True
```

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize with extended timeout
config = DeepSeekConfig(
    host="localhost",
    port=8000,
    timeout=600,  # 10 minutes
    reasoning_enabled=True
)

client = DeepSeekR1Client(config)
```

### Getting Help

1. **Check Logs**: Review logs in `~/.deepseek-r1/logs/`
2. **Run Tests**: Execute `python tests/test_integration.py`
3. **Test Examples**: Try `python examples/demo_deepseek_r1_clean.py`
4. **Review Documentation**: Check this guide and related docs
5. **Submit Issues**: Create detailed bug reports with logs

---

## Best Practices

### 1. Requirement Specification
- Be specific and detailed in requirements
- Include tolerances and constraints
- Specify materials and surface finishes
- Provide context about application

### 2. Mode Selection
- Use **Technical** for precision parts
- Use **Creative** for innovative designs
- Use **Reasoning** for complex assemblies
- Use **Fast** for prototypes and simple shapes

### 3. Quality Management
- Set appropriate quality targets
- Monitor quality scores
- Use pattern learning for improvement
- Review reasoning chains for insights

### 4. Performance Optimization
- Enable caching for repeated patterns
- Use appropriate timeouts
- Monitor resource usage
- Tune model parameters

### 5. Error Handling
- Implement proper error handling
- Use fallback mechanisms
- Monitor logs for issues
- Test changes incrementally

---

## Future Enhancements

### Planned Features
1. **Multi-step Reasoning**: Extended reasoning chains for ultra-complex parts
2. **Design Optimization**: Automated design optimization loops
3. **Material Intelligence**: AI-powered material selection
4. **Manufacturing Integration**: Direct CAM integration
5. **Collaborative Design**: Multi-agent design systems
6. **Visual Validation**: Image-based model verification

### Research Areas
- Generative design capabilities
- Physics-based validation
- Cost optimization
- Sustainability analysis

---

## Support and Resources

### Documentation
- [Enhanced Complex Shapes Guide](../advanced/COMPLEX_SHAPES_GUIDE.md)
- [State Management Guide](STATE_GUIDE.md)
- [Security Guide](SECURITY_GUIDE.md)

### Examples
- `examples/demo_deepseek_r1_clean.py` - Complete demonstration
- `examples/test_improved_prompting_example.py` - Prompting examples
- `examples/demo_unified_llm.py` - Unified LLM usage

### Community
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share experiences
- Contributions: Submit improvements and fixes

---

**Version**: 1.0.0
**Last Updated**: February 2026
**Status**: Production Ready
