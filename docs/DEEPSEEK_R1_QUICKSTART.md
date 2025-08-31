# DeepSeek R1 Integration Quick Start

## Overview

The FreeCAD LLM Automation system now includes **DeepSeek R1 integration** for generating complex mechanical parts with advanced AI reasoning capabilities.

## 🚀 Quick Setup

### 1. Install DeepSeek R1 Locally

```bash
# Run the automated setup script
chmod +x scripts/setup_deepseek_r1.sh
./scripts/setup_deepseek_r1.sh
```

### 2. Start DeepSeek R1 Server

```bash
# Start the local server
~/.deepseek-r1/start_deepseek.sh
```

### 3. Test the Integration

```bash
# Run the integration test
python tests/test_integration.py

# Run the full demo
python examples/demo_deepseek_r1_clean.py
```

## 🎯 Key Features

- **🧠 Advanced Reasoning**: Full reasoning chains for complex design decisions
- **🔧 Multiple Modes**: Technical, Creative, Fast, and Reasoning modes
- **⚙️ Complex Parts**: Support for assemblies, gears, mechanisms, and advanced geometries
- **📊 Quality Prediction**: AI-powered quality assessment and optimization
- **🔄 Smart Fallback**: Seamless fallback to other LLM providers
- **🏠 Local Privacy**: Complete control with local execution

## 📊 Generation Modes

| Mode | Use Case | Example |
|------|----------|---------|
| **Technical** | Precision engineering parts | Shafts, bearings, precision components |
| **Creative** | Innovative designs | Phone stands, artistic parts, novel mechanisms |
| **Reasoning** | Complex assemblies | Gear trains, linkages, multi-part systems |
| **Fast** | Simple parts | Basic shapes, prototypes, simple geometries |

## 🛠️ Usage Examples

### Simple Command Line

```bash
python -m ai_designer.cli \
    --deepseek-enabled \
    --deepseek-mode reasoning \
    "Create a gear assembly with 20 teeth main gear and 10 teeth pinion"
```

### Python API

```python
from ai_designer.llm.deepseek_client import DeepSeekR1Client, DeepSeekMode

# Initialize client
client = DeepSeekR1Client()

# Generate complex part
response = client.generate_complex_part(
    requirements="Create a precision shaft with keyway",
    mode=DeepSeekMode.TECHNICAL
)

print(f"Generated code: {response.generated_code}")
print(f"Confidence: {response.confidence_score:.2f}")
```

### Enhanced Complex Generator

```python
from ai_designer.core.enhanced_complex_generator import EnhancedComplexShapeGenerator

# Initialize with DeepSeek support
generator = EnhancedComplexShapeGenerator(
    llm_client=your_llm_client,
    state_analyzer=your_state_analyzer,
    command_executor=your_command_executor,
    use_deepseek=True
)

# Generate with quality targets
result = generator.generate_enhanced_complex_shape(
    user_requirements="Create a complex gear assembly",
    session_id="demo_session",
    quality_targets={'geometric_accuracy': 0.95}
)
```

## 📁 File Structure

```
freecad-llm-automation/
├── src/ai_designer/llm/
│   └── deepseek_client.py          # DeepSeek R1 client implementation
├── src/ai_designer/core/
│   └── enhanced_complex_generator.py  # Enhanced generator with DeepSeek
├── examples/
│   └── demo_deepseek_r1_clean.py   # Complete demo
├── scripts/
│   └── setup_deepseek_r1.sh        # Automated setup script
├── tests/
│   └── test_integration.py         # Integration tests
├── docs/
│   └── DEEPSEEK_R1_INTEGRATION.md  # Detailed documentation
└── config/
    └── config.yaml                 # Configuration with DeepSeek settings
```

## ⚙️ Configuration

Update `config/config.yaml`:

```yaml
deepseek:
  enabled: true
  host: "localhost"
  port: 8000
  model_name: "deepseek-r1"
  reasoning_enabled: true
  
enhanced_generator:
  use_deepseek: true
  quality_targets:
    geometric_accuracy: 0.9
    manufacturability: 0.9
```

## 🏥 Health Check

```bash
# Check if DeepSeek R1 server is running
curl http://localhost:8000/health

# Get server statistics
curl http://localhost:8000/stats
```

## 🎨 Example Generations

### Technical: Precision Shaft
```
Input: "Create a shaft with 100mm length, 20mm diameter, 5mm keyway"
Output: Complete FreeCAD code with proper tolerances and chamfers
Confidence: 0.92
Reasoning Steps: 5
```

### Creative: Phone Stand
```
Input: "Design an innovative adjustable phone stand"
Output: Modern design with cable management and multi-angle support
Confidence: 0.87
Reasoning Steps: 7
```

### Complex: Gear Assembly
```
Input: "Create a gear train with 2:1 ratio and mounting brackets"
Output: Complete assembly with proper gear mesh and clearances
Confidence: 0.89
Reasoning Steps: 12
```

## 🔧 Troubleshooting

### Server Not Starting
```bash
# Check Python dependencies
pip install torch transformers fastapi uvicorn

# Start manually with debug
cd ~/.deepseek-r1
python3 deepseek_server.py
```

### Connection Issues
```bash
# Check if port is available
netstat -tlnp | grep 8000

# Test direct connection
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1","messages":[{"role":"user","content":"test"}]}'
```

### Low Quality Results
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
- Keyway: 5mm wide, 2.5mm deep, DIN 6885
- Material: Steel C45
"""
```

## 📈 Performance Metrics

Monitor DeepSeek R1 performance:

```python
# Get performance metrics
metrics = client.get_performance_metrics()
print(f"Success rate: {metrics['success_rate']*100:.1f}%")
print(f"Average confidence: {metrics['average_confidence']:.2f}")

# Get reasoning insights
insights = client.get_reasoning_insights()
for insight in insights['insights']:
    print(f"• {insight}")
```

## 🎯 Next Steps

1. **Run the Demo**: `python examples/demo_deepseek_r1_clean.py`
2. **Read Full Documentation**: `docs/DEEPSEEK_R1_INTEGRATION.md`
3. **Integrate with Your Workflow**: See API examples above
4. **Monitor Performance**: Use built-in metrics and insights
5. **Customize for Your Needs**: Adjust modes and quality targets

## 🆘 Support

- **Setup Issues**: Check `scripts/setup_deepseek_r1.sh` logs
- **Runtime Issues**: Check server logs in `~/.deepseek-r1/logs/`
- **Integration Issues**: Run `tests/test_integration.py`
- **Quality Issues**: Adjust mode and quality targets

## 🎉 Ready to Go!

Your FreeCAD system now has access to advanced AI reasoning for complex part generation. The DeepSeek R1 integration provides:

- ✅ Local AI processing for privacy
- ✅ Advanced reasoning for complex designs
- ✅ Multiple generation modes for different use cases
- ✅ Quality prediction and optimization
- ✅ Seamless integration with existing workflows

Start creating complex mechanical parts with AI-powered reasoning today!
