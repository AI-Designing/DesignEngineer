#!/usr/bin/env python3
"""
Debug script to test socket communication with persistent GUI
"""

import socket
import json
import time

def test_gui_communication():
    """Test communication with the persistent FreeCAD GUI"""
    port = 39485  # The NEW port from the latest GUI
    
    print(f"🔍 Testing socket communication on port {port}")
    
    try:
        # Test simple connection
        print("📡 Attempting to connect...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5)
        client_socket.connect(('localhost', port))
        print("✅ Successfully connected to GUI socket")
        
        # Test sending a simple command
        test_command = {
            'type': 'execute_script',
            'script': '''
# Simple test script
import FreeCAD
doc = FreeCAD.ActiveDocument
if not doc:
    doc = FreeCAD.newDocument("TestDoc")
    
# Create a simple box for testing
box = doc.addObject("Part::Box", "TestBox")
box.Length = 5
box.Width = 5  
box.Height = 5
doc.recompute()
print("🎯 TEST: Simple box created successfully")
''',
            'timestamp': time.time()
        }
        
        print("📤 Sending test command...")
        message = json.dumps(test_command).encode('utf-8')
        client_socket.send(message)
        
        print("📥 Waiting for response...")
        response_data = client_socket.recv(4096)
        response = json.loads(response_data.decode('utf-8'))
        
        print(f"📋 Response: {response}")
        
        if response.get('status') == 'executed':
            print("✅ Command executed successfully!")
            print("🔍 Check the FreeCAD GUI - you should see a small test box")
        else:
            print("❌ Command execution failed")
            
        client_socket.close()
        return True
        
    except ConnectionRefusedError:
        print("❌ Connection refused - GUI socket server not running")
        return False
    except socket.timeout:
        print("❌ Connection timeout - GUI not responding")
        return False
    except Exception as e:
        print(f"❌ Communication error: {e}")
        return False

if __name__ == "__main__":
    success = test_gui_communication()
    if not success:
        print("\n💡 Possible issues:")
        print("   1. FreeCAD GUI socket server not started")
        print("   2. Port number mismatch")
        print("   3. GUI process crashed or hung")
        print("   4. Socket communication error")
