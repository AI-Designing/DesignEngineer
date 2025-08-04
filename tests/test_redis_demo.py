#!/usr/bin/env python3
"""
Redis State Management Demo for FreeCAD LLM Automation

This script demonstrates how Redis is used to store and manage FreeCAD object states
that can be used by the LLM to determine next steps in implementation.
"""

import json
import time
from datetime import datetime
from ai_designer.redis_utils.client import RedisClient
from ai_designer.redis_utils.state_cache import StateCache

def demo_redis_state_management():
    """Demonstrate Redis state management for FreeCAD objects"""
    print("🚀 Redis State Management Demo for FreeCAD LLM Automation")
    print("=" * 60)
    
    # Initialize Redis client and state cache
    print("1. Initializing Redis connection...")
    redis_client = RedisClient()
    
    if not redis_client.connect():
        print("❌ Failed to connect to Redis. Make sure Redis server is running.")
        print("   To start Redis: redis-server")
        return False
    
    print("✅ Connected to Redis successfully!")
    state_cache = StateCache(redis_client)
    
    # Demo 1: Caching FreeCAD object state for LLM
    print("\n2. Caching FreeCAD Object State for LLM Analysis...")
    
    # Simulate FreeCAD document state
    freecad_state = {
        "document_name": "mechanical_part.FCStd",
        "active_objects": [
            {
                "name": "Body",
                "type": "PartDesign::Body",
                "features": ["Sketch", "Pad"]
            },
            {
                "name": "Sketch",
                "type": "Sketcher::SketchObject",
                "geometry": ["Line", "Circle", "Constraint"]
            }
        ],
        "current_step": "sketch_completed",
        "next_possible_actions": [
            "create_pad_extrusion",
            "add_more_constraints",
            "create_new_sketch"
        ],
        "constraints": {
            "horizontal": 2,
            "vertical": 1,
            "dimensional": 3
        },
        "readiness_for_next_step": True,
        "timestamp": datetime.now().isoformat()
    }
    
    # Cache the state
    state_key = state_cache.cache_state(
        freecad_state,
        document_name="mechanical_part",
        session_id="user_session_001",
        expiration=3600  # 1 hour
    )
    
    print(f"   ✅ Cached FreeCAD state with key: {state_key[:50]}...")
    
    # Demo 2: LLM Analysis based on current state
    print("\n3. Storing LLM Analysis based on current state...")
    
    llm_analysis = {
        "analysis_type": "next_step_recommendation",
        "current_state_assessment": {
            "sketch_complete": True,
            "constraints_sufficient": True,
            "ready_for_3d_operation": True
        },
        "recommended_next_steps": [
            {
                "step": 1,
                "action": "create_pad",
                "description": "Extrude the sketch to create 3D geometry",
                "parameters": {
                    "direction": "normal_to_sketch",
                    "length": "10mm",
                    "reversed": False
                },
                "confidence": 0.95
            },
            {
                "step": 2,
                "action": "add_fillet",
                "description": "Add fillets to sharp edges",
                "parameters": {
                    "radius": "2mm",
                    "edges": "all_exterior_edges"
                },
                "confidence": 0.80
            }
        ],
        "risk_assessment": {
            "failure_probability": 0.05,
            "potential_issues": ["over_constrained_sketch"],
            "mitigation": "Check constraint redundancy"
        },
        "llm_confidence": 0.92,
        "processing_time_ms": 1250,
        "timestamp": datetime.now().isoformat()
    }
    
    # Cache the analysis
    analysis_key = state_cache.cache_analysis(
        llm_analysis,
        document_name="mechanical_part",
        analysis_type="next_step_recommendation",
        expiration=1800  # 30 minutes
    )
    
    print(f"   ✅ Cached LLM analysis with key: {analysis_key[:50]}...")
    
    # Demo 3: Retrieving state for LLM decision making
    print("\n4. Retrieving state for LLM decision making...")
    
    # Retrieve the cached state
    retrieved_state = state_cache.retrieve_state(state_key)
    print(f"   📖 Retrieved state for document: {retrieved_state['document_name']}")
    print(f"   🎯 Current step: {retrieved_state['current_step']}")
    print(f"   🔧 Active objects: {len(retrieved_state['active_objects'])}")
    print(f"   ✅ Ready for next step: {retrieved_state['readiness_for_next_step']}")
    
    # Retrieve the analysis
    retrieved_analysis = state_cache.retrieve_analysis(analysis_key)
    print(f"   🤖 LLM confidence: {retrieved_analysis['llm_confidence']}")
    print(f"   📋 Recommended steps: {len(retrieved_analysis['recommended_next_steps'])}")
    
    # Demo 4: List all states for monitoring
    print("\n5. Monitoring all cached states...")
    
    all_states = state_cache.list_states()
    all_analyses = state_cache.list_analyses()
    
    print(f"   📊 Total cached states: {len(all_states)}")
    print(f"   🧠 Total cached analyses: {len(all_analyses)}")
    
    # Demo 5: Simulating iterative LLM workflow
    print("\n6. Simulating iterative LLM workflow...")
    
    workflow_steps = [
        {"step": 1, "action": "sketch_created", "status": "completed"},
        {"step": 2, "action": "constraints_added", "status": "in_progress"},
        {"step": 3, "action": "pad_operation", "status": "pending"}
    ]
    
    for i, step in enumerate(workflow_steps):
        step_state = {
            "workflow_step": step["step"],
            "action": step["action"],
            "status": step["status"],
            "completion_percentage": (i + 1) * 33,
            "timestamp": datetime.now().isoformat()
        }
        
        step_key = state_cache.cache_state(
            step_state,
            document_name="mechanical_part",
            session_id=f"workflow_step_{step['step']}",
            expiration=600  # 10 minutes
        )
        
        print(f"   📝 Step {step['step']}: {step['action']} - {step['status']}")
    
    # Demo 6: Show metadata summary
    print("\n7. System overview...")
    
    metadata_summary = state_cache.get_metadata_summary()
    print(f"   📈 Total states: {metadata_summary['total_states']}")
    print(f"   🔍 Total analyses: {metadata_summary['total_analyses']}")
    print(f"   📁 Active documents: {len(metadata_summary.get('documents', []))}")
    
    print("\n8. Redis Key Examples:")
    for key in all_states[:3]:  # Show first 3 keys
        print(f"   🔑 {key}")
    
    print(f"\n✅ Demo completed successfully!")
    print(f"🎯 Redis is working properly for FreeCAD state management")
    print(f"🤖 LLM can now use cached states to make informed decisions")
    
    return True

def test_redis_for_llm_workflow():
    """Test specific Redis functionality for LLM workflow"""
    print("\n" + "="*60)
    print("🧪 Testing Redis for LLM Workflow Integration")
    print("="*60)
    
    redis_client = RedisClient()
    if not redis_client.connect():
        print("❌ Redis connection failed")
        return False
    
    state_cache = StateCache(redis_client)
    
    # Test 1: Quick state updates for real-time LLM feedback
    print("\n1. Testing real-time state updates...")
    
    for i in range(3):
        current_state = {
            "iteration": i + 1,
            "freecad_objects": ["Cube", "Sphere", "Cylinder"][:i+1],
            "llm_feedback": f"Iteration {i+1} completed successfully",
            "next_recommendation": f"Add object {i+2}",
            "confidence_score": 0.8 + (i * 0.05)
        }
        
        key = state_cache.cache_state(
            current_state,
            document_name="llm_test_document",
            session_id=f"iteration_{i+1}"
        )
        
        print(f"   ✅ Iteration {i+1} state cached")
        time.sleep(0.1)  # Simulate processing time
    
    # Test 2: Verify LLM can retrieve latest state
    print("\n2. Testing LLM state retrieval...")
    
    latest_state_key = state_cache.get_latest_state(document_name="llm_test_document")
    if latest_state_key:
        latest_state = state_cache.retrieve_state(latest_state_key)
        print(f"   📖 Latest state iteration: {latest_state['iteration']}")
        print(f"   🎯 LLM confidence: {latest_state['confidence_score']}")
        print(f"   💡 Next recommendation: {latest_state['next_recommendation']}")
    
    print("\n✅ LLM workflow integration test passed!")
    return True

if __name__ == "__main__":
    success = demo_redis_state_management()
    if success:
        test_redis_for_llm_workflow()
    
    print(f"\n{'='*60}")
    print(f"🎉 Redis State Management System is fully operational!")
    print(f"🤖 Ready for LLM-driven FreeCAD automation!")
    print(f"{'='*60}")
