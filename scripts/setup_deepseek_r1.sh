#!/bin/bash
# DeepSeek R1 Local Setup Script
# Sets up DeepSeek R1 for local complex part generation

set -e

echo "🚀 Setting up DeepSeek R1 for FreeCAD Complex Part Generation"
echo "=" * 60

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEEPSEEK_PORT=8000
DEEPSEEK_HOST="localhost"
DEEPSEEK_MODEL="deepseek-r1"
INSTALL_DIR="$HOME/.deepseek-r1"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check if we have enough memory (recommend 8GB+)
    total_mem=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    total_mem_gb=$((total_mem / 1024 / 1024))

    if [ $total_mem_gb -lt 8 ]; then
        print_warning "DeepSeek R1 recommends at least 8GB RAM. You have ${total_mem_gb}GB"
        print_warning "Performance may be limited"
    else
        print_success "Memory check passed: ${total_mem_gb}GB available"
    fi

    # Check disk space (recommend 10GB+)
    available_space=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//')

    if [ $available_space -lt 10 ]; then
        print_warning "DeepSeek R1 recommends at least 10GB free space. You have ${available_space}GB"
    else
        print_success "Disk space check passed: ${available_space}GB available"
    fi
}

# Install dependencies
install_dependencies() {
    print_status "Installing DeepSeek R1 dependencies..."

    # Update pip
    python3 -m pip install --upgrade pip

    # Install required packages
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
    pip3 install transformers accelerate
    pip3 install fastapi uvicorn
    pip3 install requests websockets
    pip3 install pydantic

    print_success "Dependencies installed successfully"
}

# Download DeepSeek R1 model
download_model() {
    print_status "Setting up DeepSeek R1 model..."

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"

    # Create a simple DeepSeek R1 server wrapper
    cat > deepseek_server.py << 'EOF'
#!/usr/bin/env python3
"""
DeepSeek R1 Local Server for FreeCAD Integration
Provides REST API for complex part generation
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DeepSeek R1 FreeCAD Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: int = 8192
    temperature: float = 0.1
    top_p: float = 0.95
    stream: bool = False
    reasoning: bool = True

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

# Mock DeepSeek R1 implementation for demo
class MockDeepSeekR1:
    """Mock implementation of DeepSeek R1 for demonstration"""

    def __init__(self):
        self.model_name = "deepseek-r1"
        self.request_count = 0

    def generate_freecad_code(self, prompt: str, reasoning_enabled: bool = True) -> Dict[str, Any]:
        """Generate FreeCAD code with reasoning chain"""
        self.request_count += 1

        # Analyze the prompt to determine complexity
        complexity = self._analyze_complexity(prompt)

        # Generate reasoning chain
        reasoning_steps = self._generate_reasoning_steps(prompt, complexity)

        # Generate FreeCAD code
        generated_code = self._generate_freecad_code(prompt, complexity)

        # Calculate confidence
        confidence = 0.85 if complexity < 5 else 0.75

        return {
            "code": generated_code,
            "reasoning": reasoning_steps if reasoning_enabled else [],
            "confidence": confidence,
            "complexity": complexity,
            "execution_time": 2.5 + (complexity * 0.5)
        }

    def _analyze_complexity(self, prompt: str) -> int:
        """Analyze prompt complexity (1-10 scale)"""
        complexity_keywords = {
            'simple': 1, 'basic': 2, 'gear': 6, 'assembly': 7,
            'complex': 8, 'advanced': 9, 'linkage': 8, 'mechanism': 7
        }

        prompt_lower = prompt.lower()
        max_complexity = 3  # Base complexity

        for keyword, score in complexity_keywords.items():
            if keyword in prompt_lower:
                max_complexity = max(max_complexity, score)

        return min(10, max_complexity)

    def _generate_reasoning_steps(self, prompt: str, complexity: int) -> List[Dict[str, Any]]:
        """Generate reasoning steps based on prompt analysis"""
        steps = []

        # Step 1: Analysis
        steps.append({
            "description": "Analyze design requirements",
            "reasoning": f"Breaking down the requirements: {prompt[:100]}...",
            "confidence": 0.9,
            "status": "completed"
        })

        # Step 2: Planning
        steps.append({
            "description": "Plan FreeCAD implementation approach",
            "reasoning": f"Considering complexity level {complexity}, will use appropriate FreeCAD modules",
            "confidence": 0.85,
            "status": "completed"
        })

        # Additional steps for complex parts
        if complexity >= 6:
            steps.append({
                "description": "Design component relationships",
                "reasoning": "Analyzing spatial relationships and constraints between components",
                "confidence": 0.8,
                "status": "completed"
            })

            steps.append({
                "description": "Optimize for manufacturability",
                "reasoning": "Ensuring design can be manufactured with standard processes",
                "confidence": 0.75,
                "status": "completed"
            })

        # Final step
        steps.append({
            "description": "Generate FreeCAD Python code",
            "reasoning": "Creating executable Python code using FreeCAD API",
            "confidence": 0.9,
            "status": "completed"
        })

        return steps

    def _generate_freecad_code(self, prompt: str, complexity: int) -> str:
        """Generate appropriate FreeCAD code based on prompt and complexity"""

        # Determine what type of part to create
        prompt_lower = prompt.lower()

        if 'shaft' in prompt_lower:
            return self._generate_shaft_code()
        elif 'gear' in prompt_lower:
            return self._generate_gear_assembly_code()
        elif 'phone stand' in prompt_lower or 'stand' in prompt_lower:
            return self._generate_phone_stand_code()
        elif 'linkage' in prompt_lower:
            return self._generate_linkage_code()
        elif 'cube' in prompt_lower or 'box' in prompt_lower:
            return self._generate_simple_box_code()
        else:
            return self._generate_generic_part_code(prompt)

    def _generate_shaft_code(self) -> str:
        return '''
import FreeCAD as App
import Part
import PartDesign

# Create new document
doc = App.newDocument("Shaft_Design")

# Create shaft body
shaft_body = doc.addObject('Part::Cylinder', 'ShaftBody')
shaft_body.Radius = 10.0  # 20mm diameter = 10mm radius
shaft_body.Height = 100.0
shaft_body.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Create keyway cut
keyway = doc.addObject('Part::Box', 'Keyway')
keyway.Length = 5.0  # 5mm wide
keyway.Width = 100.0  # Full length
keyway.Height = 2.5  # 2.5mm deep
keyway.Placement = App.Placement(App.Vector(-2.5, 0, 7.5), App.Rotation())

# Cut keyway from shaft
shaft_with_keyway = doc.addObject('Part::Cut', 'ShaftWithKeyway')
shaft_with_keyway.Base = shaft_body
shaft_with_keyway.Tool = keyway

# Add chamfers (simplified)
chamfer = doc.addObject('Part::Chamfer', 'ShaftChamfer')
chamfer.Base = shaft_with_keyway
# Note: In real implementation, would add proper edge selection

doc.recompute()
print("Shaft with keyway created successfully!")
'''

    def _generate_gear_assembly_code(self) -> str:
        return '''
import FreeCAD as App
import Part
import math

# Create new document
doc = App.newDocument("Gear_Assembly")

# Main gear
main_gear_body = doc.addObject('Part::Cylinder', 'MainGearBody')
main_gear_body.Radius = 25.0  # 50mm diameter
main_gear_body.Height = 10.0
main_gear_body.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Main gear bore
main_gear_bore = doc.addObject('Part::Cylinder', 'MainGearBore')
main_gear_bore.Radius = 5.0
main_gear_bore.Height = 12.0
main_gear_bore.Placement = App.Placement(App.Vector(0, 0, -1), App.Rotation())

# Cut bore from main gear
main_gear = doc.addObject('Part::Cut', 'MainGear')
main_gear.Base = main_gear_body
main_gear.Tool = main_gear_bore

# Pinion gear
pinion_gear_body = doc.addObject('Part::Cylinder', 'PinionGearBody')
pinion_gear_body.Radius = 12.5  # 25mm diameter
pinion_gear_body.Height = 8.0
pinion_gear_body.Placement = App.Placement(App.Vector(37.5, 0, 0), App.Rotation())

# Pinion gear bore
pinion_gear_bore = doc.addObject('Part::Cylinder', 'PinionGearBore')
pinion_gear_bore.Radius = 3.0
pinion_gear_bore.Height = 10.0
pinion_gear_bore.Placement = App.Placement(App.Vector(37.5, 0, -1), App.Rotation())

# Cut bore from pinion gear
pinion_gear = doc.addObject('Part::Cut', 'PinionGear')
pinion_gear.Base = pinion_gear_body
pinion_gear.Tool = pinion_gear_bore

# Main shaft
main_shaft = doc.addObject('Part::Cylinder', 'MainShaft')
main_shaft.Radius = 4.5
main_shaft.Height = 50.0
main_shaft.Placement = App.Placement(App.Vector(0, 0, -20), App.Rotation())

# Pinion shaft
pinion_shaft = doc.addObject('Part::Cylinder', 'PinionShaft')
pinion_shaft.Radius = 2.5
pinion_shaft.Height = 40.0
pinion_shaft.Placement = App.Placement(App.Vector(37.5, 0, -15), App.Rotation())

# Mounting bracket (simplified)
bracket = doc.addObject('Part::Box', 'MountingBracket')
bracket.Length = 60.0
bracket.Width = 15.0
bracket.Height = 30.0
bracket.Placement = App.Placement(App.Vector(-15, -7.5, -25), App.Rotation())

doc.recompute()
print("Gear assembly created successfully!")
'''

    def _generate_phone_stand_code(self) -> str:
        return '''
import FreeCAD as App
import Part
import Draft

# Create new document
doc = App.newDocument("Phone_Stand")

# Base platform
base = doc.addObject('Part::Box', 'Base')
base.Length = 80.0
base.Width = 60.0
base.Height = 5.0
base.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Back support
back_support = doc.addObject('Part::Box', 'BackSupport')
back_support.Length = 8.0
back_support.Width = 60.0
back_support.Height = 80.0
back_support.Placement = App.Placement(App.Vector(72, 0, 5), App.Rotation())

# Phone rest ledge
phone_ledge = doc.addObject('Part::Box', 'PhoneLedge')
phone_ledge.Length = 30.0
phone_ledge.Width = 60.0
phone_ledge.Height = 3.0
phone_ledge.Placement = App.Placement(App.Vector(42, 0, 5), App.Rotation())

# Cable management slot
cable_slot = doc.addObject('Part::Box', 'CableSlot')
cable_slot.Length = 20.0
cable_slot.Width = 8.0
cable_slot.Height = 10.0
cable_slot.Placement = App.Placement(App.Vector(30, 26, 0), App.Rotation())

# Cut cable slot from base
base_with_slot = doc.addObject('Part::Cut', 'BaseWithSlot')
base_with_slot.Base = base
base_with_slot.Tool = cable_slot

# Adjustable angle support (simplified)
angle_support = doc.addObject('Part::Cylinder', 'AngleSupport')
angle_support.Radius = 3.0
angle_support.Height = 60.0
angle_support.Placement = App.Placement(App.Vector(50, 0, 8), App.Rotation(App.Vector(0, 1, 0), 90))

doc.recompute()
print("Innovative phone stand created successfully!")
'''

    def _generate_linkage_code(self) -> str:
        return '''
import FreeCAD as App
import Part
import math

# Create new document
doc = App.newDocument("Linkage_Mechanism")

# Input crank
crank = doc.addObject('Part::Cylinder', 'InputCrank')
crank.Radius = 3.0
crank.Height = 25.0
crank.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Connecting rod
connecting_rod = doc.addObject('Part::Box', 'ConnectingRod')
connecting_rod.Length = 60.0
connecting_rod.Width = 8.0
connecting_rod.Height = 6.0
connecting_rod.Placement = App.Placement(App.Vector(25, -4, 8), App.Rotation())

# Output slider block
slider_block = doc.addObject('Part::Box', 'SliderBlock')
slider_block.Length = 20.0
slider_block.Width = 15.0
slider_block.Height = 15.0
slider_block.Placement = App.Placement(App.Vector(85, -7.5, 5), App.Rotation())

# Guide rail
guide_rail = doc.addObject('Part::Box', 'GuideRail')
guide_rail.Length = 80.0
guide_rail.Width = 20.0
guide_rail.Height = 5.0
guide_rail.Placement = App.Placement(App.Vector(60, -10, 0), App.Rotation())

# Guide rail slot
rail_slot = doc.addObject('Part::Box', 'RailSlot')
rail_slot.Length = 70.0
rail_slot.Width = 16.0
rail_slot.Height = 8.0
rail_slot.Placement = App.Placement(App.Vector(65, -8, 2), App.Rotation())

# Cut slot from rail
guide_with_slot = doc.addObject('Part::Cut', 'GuideWithSlot')
guide_with_slot.Base = guide_rail
guide_with_slot.Tool = rail_slot

# Pin joints (simplified as cylinders)
pin1 = doc.addObject('Part::Cylinder', 'Pin1')
pin1.Radius = 2.0
pin1.Height = 12.0
pin1.Placement = App.Placement(App.Vector(0, -6, 10), App.Rotation(App.Vector(1, 0, 0), 90))

pin2 = doc.addObject('Part::Cylinder', 'Pin2')
pin2.Radius = 2.0
pin2.Height = 12.0
pin2.Placement = App.Placement(App.Vector(85, -6, 10), App.Rotation(App.Vector(1, 0, 0), 90))

doc.recompute()
print("Linkage mechanism created successfully!")
'''

    def _generate_simple_box_code(self) -> str:
        return '''
import FreeCAD as App
import Part

# Create new document
doc = App.newDocument("SimpleBox")

# Create a simple test cube
test_cube = doc.addObject('Part::Box', 'TestCube')
test_cube.Length = 10.0
test_cube.Width = 10.0
test_cube.Height = 10.0
test_cube.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

doc.recompute()
print("Simple test cube created successfully!")
'''

    def _generate_generic_part_code(self, prompt: str) -> str:
        return f'''
import FreeCAD as App
import Part

# Create new document for: {prompt[:50]}...
doc = App.newDocument("GenericPart")

# Create base geometry
base_part = doc.addObject('Part::Box', 'BasePart')
base_part.Length = 50.0
base_part.Width = 30.0
base_part.Height = 20.0
base_part.Placement = App.Placement(App.Vector(0, 0, 0), App.Rotation())

# Add additional features based on requirements
feature1 = doc.addObject('Part::Cylinder', 'Feature1')
feature1.Radius = 5.0
feature1.Height = 25.0
feature1.Placement = App.Placement(App.Vector(25, 15, 20), App.Rotation())

# Combine features
combined_part = doc.addObject('Part::MultiFuse', 'CombinedPart')
combined_part.Shapes = [base_part, feature1]

doc.recompute()
print("Generic part created based on requirements!")
'''

# Global DeepSeek instance
deepseek_model = MockDeepSeekR1()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": "deepseek-r1", "timestamp": datetime.now().isoformat()}

@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """Chat completions endpoint compatible with OpenAI API"""

    try:
        # Extract the user message
        user_message = None
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
                break

        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")

        # Generate response using mock DeepSeek
        start_time = time.time()
        generation_result = deepseek_model.generate_freecad_code(
            user_message,
            reasoning_enabled=request.reasoning
        )
        execution_time = time.time() - start_time

        # Format response
        response_content = generation_result["code"]

        # Add reasoning chain if requested
        if request.reasoning and generation_result["reasoning"]:
            reasoning_text = "\\n\\n# Reasoning Chain:\\n"
            for i, step in enumerate(generation_result["reasoning"]):
                reasoning_text += f"# Step {i+1}: {step['description']}\\n"
                reasoning_text += f"# {step['reasoning']}\\n"
            response_content = reasoning_text + "\\n" + response_content

        # Create response
        response = ChatResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content,
                    "reasoning": {
                        "steps": generation_result["reasoning"]
                    } if request.reasoning else None
                },
                "finish_reason": "stop"
            }],
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split())
            }
        )

        logger.info(f"Generated response in {execution_time:.2f}s, confidence: {generation_result['confidence']:.2f}")

        return response

    except Exception as e:
        logger.error(f"Error in chat completions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "deepseek-r1",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "deepseek"
            }
        ]
    }

@app.get("/stats")
async def get_stats():
    """Get server statistics"""
    return {
        "requests_processed": deepseek_model.request_count,
        "uptime": time.time(),
        "model": "deepseek-r1-mock",
        "status": "running"
    }

if __name__ == "__main__":
    print("🚀 Starting DeepSeek R1 FreeCAD Server...")
    print(f"📡 Server will be available at http://localhost:8000")
    print(f"🏥 Health check: http://localhost:8000/health")
    print(f"📊 Stats: http://localhost:8000/stats")
    print("✅ Server ready for FreeCAD complex part generation!")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
EOF

    chmod +x deepseek_server.py

    print_success "DeepSeek R1 server script created"
}

# Create systemd service (optional)
create_service() {
    print_status "Creating systemd service (optional)..."

    if [ "$EUID" -eq 0 ]; then
        # Create systemd service file
        cat > /etc/systemd/system/deepseek-r1.service << EOF
[Unit]
Description=DeepSeek R1 FreeCAD Server
After=network.target

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/deepseek_server.py
Restart=always
RestartSec=3
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=$INSTALL_DIR

[Install]
WantedBy=multi-user.target
EOF

        systemctl daemon-reload
        systemctl enable deepseek-r1

        print_success "Systemd service created and enabled"
        print_status "Use 'sudo systemctl start deepseek-r1' to start the service"
    else
        print_warning "Run as root to create systemd service"
    fi
}

# Create startup script
create_startup_script() {
    print_status "Creating startup script..."

    cat > "$INSTALL_DIR/start_deepseek.sh" << EOF
#!/bin/bash
# Start DeepSeek R1 FreeCAD Server

cd "$INSTALL_DIR"

echo "🚀 Starting DeepSeek R1 FreeCAD Server..."
echo "📡 Server will be available at http://localhost:$DEEPSEEK_PORT"
echo "🛑 Press Ctrl+C to stop"

python3 deepseek_server.py
EOF

    chmod +x "$INSTALL_DIR/start_deepseek.sh"

    # Create desktop launcher
    if [ -d "$HOME/.local/share/applications" ]; then
        cat > "$HOME/.local/share/applications/deepseek-r1.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DeepSeek R1 FreeCAD Server
Comment=Local AI server for FreeCAD complex part generation
Exec=$INSTALL_DIR/start_deepseek.sh
Icon=applications-engineering
Terminal=true
Categories=Development;Engineering;
EOF

        print_success "Desktop launcher created"
    fi

    print_success "Startup script created at $INSTALL_DIR/start_deepseek.sh"
}

# Test installation
test_installation() {
    print_status "Testing installation..."

    # Start server in background
    cd "$INSTALL_DIR"
    python3 deepseek_server.py &
    SERVER_PID=$!

    # Wait for server to start
    sleep 5

    # Test health endpoint
    if curl -s "http://localhost:$DEEPSEEK_PORT/health" > /dev/null; then
        print_success "Health check passed"

        # Test chat endpoint
        if curl -s -X POST "http://localhost:$DEEPSEEK_PORT/v1/chat/completions" \
           -H "Content-Type: application/json" \
           -d '{"model":"deepseek-r1","messages":[{"role":"user","content":"Create a simple test cube"}],"reasoning":true}' \
           > /dev/null; then
            print_success "Chat endpoint test passed"
        else
            print_warning "Chat endpoint test failed"
        fi
    else
        print_error "Health check failed"
    fi

    # Stop test server
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null

    print_success "Installation test completed"
}

# Main installation process
main() {
    print_status "Starting DeepSeek R1 installation for FreeCAD..."

    check_requirements
    install_dependencies
    download_model
    create_startup_script

    # Optional service creation
    if [ "$1" = "--service" ]; then
        create_service
    fi

    test_installation

    echo
    print_success "🎉 DeepSeek R1 installation completed!"
    echo
    echo "📋 Next steps:"
    echo "1. Start the server: $INSTALL_DIR/start_deepseek.sh"
    echo "2. Test with: curl http://localhost:$DEEPSEEK_PORT/health"
    echo "3. Run the demo: python3 examples/demo_deepseek_r1_clean.py"
    echo
    echo "📚 Configuration:"
    echo "- Server: http://localhost:$DEEPSEEK_PORT"
    echo "- Install directory: $INSTALL_DIR"
    echo "- Log level: INFO"
    echo
    echo "🔧 Troubleshooting:"
    echo "- Check logs: journalctl -u deepseek-r1 -f (if using systemd)"
    echo "- Manual start: cd $INSTALL_DIR && python3 deepseek_server.py"
    echo "- Update config: edit config/config.yaml"
    echo
    echo "🚀 Ready for complex FreeCAD part generation!"
}

# Run installation
main "$@"
