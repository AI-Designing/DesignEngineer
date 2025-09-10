# DeepSeek R1 Integration for FreeCAD Complex Parts

This guide covers the integration of DeepSeek R1 with the FreeCAD automation system for generating complex mechanical parts with advanced reasoning capabilities.

## Overview

The DeepSeek R1 integration provides:

- **Advanced Reasoning**: Full reasoning chains for complex design decisions
- **Multiple Generation Modes**: Technical, Creative, Fast, and Reasoning modes
- **Complex Part Generation**: Support for assemblies, mechanisms, and advanced geometries
- **Quality Prediction**: AI-powered quality assessment and optimization
- **Fallback Support**: Seamless fallback to other LLM providers
- **Local Execution**: Complete privacy and control over the generation process

## Architecture

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

## Installation

### Quick Setup

Run the automated setup script:

```bash
cd freecad-llm-automation
chmod +x scripts/setup_deepseek_r1.sh
./scripts/setup_deepseek_r1.sh
```

### Manual Setup

1. **Install Dependencies**:
   ```bash
   pip install torch transformers accelerate fastapi uvicorn
   ```

2. **Configure DeepSeek R1**:
   ```yaml
   # config/config.yaml
   deepseek:
     enabled: true
     host: "localhost"
     port: 8000
     model_name: "deepseek-r1"
     timeout: 300
     reasoning_enabled: true
   ```

3. **Start Local Server**:
   ```bash
   cd ~/.deepseek-r1
   python3 deepseek_server.py
   ```

## Usage

### Basic Integration

```python
from ai_designer.llm.deepseek_client import DeepSeekR1Client, DeepSeekConfig, DeepSeekMode
from ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator

# Initialize DeepSeek client
config = DeepSeekConfig(host="localhost", port=8000)
deepseek_client = DeepSeekR1Client(config)

# Initialize enhanced generator with DeepSeek
generator = EnhancedComplexShapeGenerator(
    llm_client=None,  # Will use DeepSeek as primary
    state_analyzer=state_analyzer,
    command_executor=command_executor,
    use_deepseek=True,
    deepseek_config=config
)

# Generate complex part
result = generator.generate_enhanced_complex_shape(
    user_requirements="Create a precision gear assembly with 20 teeth",
    session_id="demo_session",
    quality_targets={'geometric_accuracy': 0.95}
)
```

### Generation Modes

#### Technical Mode
For precision engineering parts:
```python
response = deepseek_client.generate_complex_part(
    requirements="Create a precision shaft with keyway and tolerances",
    mode=DeepSeekMode.TECHNICAL,
    constraints={
        'tolerance': 0.01,
        'surface_finish': 'precision_ground',
        'material': 'steel'
    }
)
```

#### Creative Mode
For innovative designs:
```python
response = deepseek_client.generate_complex_part(
    requirements="Design an innovative phone stand with adjustable angles",
    mode=DeepSeekMode.CREATIVE,
    context={
        'target_market': 'premium',
        'manufacturing': '3D_printing'
    }
)
```

#### Reasoning Mode
For complex mechanical systems:
```python
response = deepseek_client.generate_complex_part(
    requirements="Design a linkage mechanism for motion conversion",
    mode=DeepSeekMode.REASONING
)

# Access reasoning chain
for step in response.reasoning_chain:
    print(f"Step: {step.description}")
    print(f"Reasoning: {step.reasoning}")
    print(f"Confidence: {step.confidence}")
```

### Integration Manager

The Integration Manager provides intelligent fallback and hybrid modes:

```python
from ai_designer.llm.deepseek_client import DeepSeekIntegrationManager

manager = DeepSeekIntegrationManager(deepseek_client, fallback_client)

# Auto mode - system selects best approach
code = manager.generate_command("Create a complex gear train", mode="auto")

# Hybrid mode - combines DeepSeek with validation
code = manager.generate_command("Design precision bearing", mode="hybrid")

# Get integration metrics
metrics = manager.get_integration_metrics()
print(f"DeepSeek usage: {metrics['deepseek_usage_rate']*100:.1f}%")
```

## Configuration

### DeepSeek Configuration

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
```

### Enhanced Generator Settings

```yaml
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

## API Reference

### DeepSeekR1Client

#### Methods

- `generate_complex_part(requirements, mode, context, constraints)`: Generate complex parts
- `get_performance_metrics()`: Get client performance statistics
- `get_reasoning_insights()`: Get reasoning pattern analysis

#### Response Structure

```python
@dataclass
class DeepSeekResponse:
    status: str
    generated_code: str
    reasoning_chain: List[ReasoningStep]
    confidence_score: float
    execution_time: float
    complexity_analysis: Dict[str, Any]
    optimization_suggestions: List[str]
```

### DeepSeekIntegrationManager

#### Methods

- `generate_command(nl_command, state, mode)`: Generate with intelligent mode selection
- `get_integration_metrics()`: Get usage statistics
- `_select_optimal_mode(nl_command, state)`: Auto-select generation mode

## Examples

### Simple Mechanical Part

```python
requirements = """
Create a simple shaft with:
- Length: 100mm
- Diameter: 20mm
- Keyway: 5mm wide, 2.5mm deep
- Chamfer: 1mm on both ends
"""

response = deepseek_client.generate_complex_part(
    requirements=requirements,
    mode=DeepSeekMode.TECHNICAL,
    constraints={
        'material': 'steel',
        'tolerance': 0.05,
        'surface_finish': 'machined'
    }
)
```

### Complex Assembly

```python
requirements = """
Create a gear assembly with:
1. Main gear: 50mm diameter, 20 teeth, 10mm thick
2. Pinion gear: 25mm diameter, 10 teeth, 8mm thick
3. Mounting bracket for both gears
4. Proper gear mesh and clearances
"""

response = deepseek_client.generate_complex_part(
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
```

### Creative Design

```python
requirements = """
Design an innovative phone stand that:
- Adjusts to multiple viewing angles
- Accommodates different phone sizes
- Has modern aesthetic
- Includes cable management
"""

response = deepseek_client.generate_complex_part(
    requirements=requirements,
    mode=DeepSeekMode.CREATIVE,
    context={
        'target_market': 'premium',
        'manufacturing': '3D_printing',
        'material': 'sustainable'
    }
)
```

## Performance Optimization

### Quality Targets

Set specific quality targets for generation:

```python
quality_targets = {
    'geometric_accuracy': 0.95,
    'design_consistency': 0.90,
    'aesthetic_quality': 0.85,
    'manufacturability': 0.95,
    'performance_score': 0.90
}

result = generator.generate_enhanced_complex_shape(
    user_requirements=requirements,
    session_id=session_id,
    quality_targets=quality_targets
)
```

### Pattern Learning

Enable pattern learning for improved performance:

```python
# Learn from successful generations
generator.pattern_learning.learn_from_generation(
    requirements, enhanced_plan, generation_result
)

# Find similar patterns for optimization
similar_patterns = generator.pattern_learning.find_similar_patterns(requirements)

# Get optimization suggestions
optimizations = generator.pattern_learning.get_optimization_suggestions(current_plan)
```

## Monitoring and Debugging

### Performance Metrics

```python
# Get DeepSeek performance metrics
metrics = deepseek_client.get_performance_metrics()
print(f"Success rate: {metrics['success_rate']*100:.1f}%")
print(f"Average confidence: {metrics['average_confidence']:.2f}")
print(f"Average response time: {metrics['average_response_time']:.2f}s")

# Get reasoning insights
insights = deepseek_client.get_reasoning_insights()
for insight in insights['insights']:
    print(f"• {insight}")
```

### Integration Statistics

```python
# Get integration manager statistics
stats = integration_manager.get_integration_metrics()
print(f"DeepSeek usage: {stats['deepseek_usage_rate']*100:.1f}%")
print(f"Fallback usage: {stats['fallback_usage_rate']*100:.1f}%")
print(f"Total requests: {stats['total_requests']}")
```

### Health Monitoring

```python
# Test DeepSeek connection
health_status = generator.test_deepseek_connection()
if health_status['status'] == 'success':
    print("✅ DeepSeek R1 is healthy")
    print(f"Confidence: {health_status['test_generation']['confidence']:.2f}")
else:
    print(f"❌ DeepSeek R1 issue: {health_status['error']}")
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   ```bash
   # Check if server is running
   curl http://localhost:8000/health

   # Start server manually
   cd ~/.deepseek-r1
   python3 deepseek_server.py
   ```

2. **Low Quality Scores**
   ```python
   # Adjust quality targets
   quality_targets = {
       'geometric_accuracy': 0.8,  # Lower threshold
       'design_consistency': 0.75
   }

   # Use technical mode for precision
   mode = DeepSeekMode.TECHNICAL
   ```

3. **Slow Response Times**
   ```python
   # Use fast mode for simple parts
   mode = DeepSeekMode.FAST

   # Reduce max_tokens
   config = DeepSeekConfig(max_tokens=4096)
   ```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable DeepSeek debug mode
config = DeepSeekConfig(
    host="localhost",
    port=8000,
    timeout=600,  # Longer timeout for debugging
    reasoning_enabled=True
)
```

### Performance Tuning

1. **Model Parameters**:
   ```python
   config = DeepSeekConfig(
       temperature=0.05,  # More deterministic
       top_p=0.9,         # Focused sampling
       max_tokens=6144    # Balanced length
   )
   ```

2. **Caching**:
   ```python
   # Enable pattern caching
   generator.pattern_learning.enabled = True
   generator.pattern_learning.max_patterns = 1000
   ```

3. **Parallel Processing**:
   ```python
   # Use parallel mode for complex assemblies
   result = generator.generate_enhanced_complex_shape(
       user_requirements=requirements,
       session_id=session_id,
       generation_mode=GenerationMode.PARALLEL
   )
   ```

## Integration with Existing Workflow

### Command Line Interface

```bash
# Run with DeepSeek integration
python -m ai_designer.cli \
    --deepseek-enabled \
    --deepseek-mode reasoning \
    --quality-target 0.9 \
    "Create a precision gear assembly"
```

### Web Interface

The DeepSeek integration works seamlessly with the existing web interface:

1. Enable DeepSeek in configuration
2. Select generation mode in UI
3. Set quality targets
4. Monitor reasoning chain in real-time

### API Integration

```python
# REST API endpoint
POST /api/v1/generate/complex
{
    "requirements": "Create gear assembly",
    "use_deepseek": true,
    "mode": "reasoning",
    "quality_targets": {
        "geometric_accuracy": 0.95
    }
}
```

## Future Enhancements

- **Advanced Reasoning**: Multi-step reasoning chains
- **Design Optimization**: Automated design optimization loops
- **Material Selection**: AI-powered material recommendations
- **Manufacturing Integration**: Direct CAM integration
- **Collaborative Design**: Multi-agent design systems

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review logs in `~/.deepseek-r1/logs/`
3. Test with `demo_deepseek_r1_clean.py`
4. Submit issues with detailed error logs

## License

This DeepSeek R1 integration is part of the FreeCAD LLM Automation project and follows the same MIT license terms.
