import socket
import json
import time
import traceback

def debug_enrollment_step_by_step():
    """Debug enrollment step by step"""
    server_host = 'localhost'
    server_port = 8889
    
    print("🔍 Debugging enrollment process step by step...")
    
    # Test 1: Just connect to server
    print("\n=== Test 1: Connect to server ===")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((server_host, server_port))
        print("✅ Connected to server")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    # Test 2: Login
    print("\n=== Test 2: Login ===")
    login_data = {
        'type': 'login_account',
        'username': 'yannick',
        'password': 'yann2035'
    }
    
    try:
        sock.send(json.dumps(login_data).encode('utf-8'))
        response = sock.recv(4096).decode('utf-8')
        login_response = json.loads(response)
        print(f"Login response: {login_response}")
        
        if login_response.get('status') != 'success':
            print("❌ Login failed")
            sock.close()
            return
            
        session_token = login_response['session_token']
        print(f"✅ Login successful")
    except Exception as e:
        print(f"❌ Login error: {e}")
        traceback.print_exc()
        sock.close()
        return
    
    # Test 3: Send enrollment with minimal data
    print("\n=== Test 3: Minimal enrollment ===")
    enrollment_data = {
        'type': 'enrollment_request',
        'node_id': 'debug_node',
        'session_token': session_token,
        'storage_capacity': 1.0
    }
    
    try:
        print(f"Sending enrollment data: {enrollment_data}")
        sock.send(json.dumps(enrollment_data).encode('utf-8'))
        print("✅ Enrollment request sent")
        
        # Wait for response
        response = sock.recv(4096).decode('utf-8')
        print(f"✅ Received response: {response[:200]}...")
        
        enrollment_response = json.loads(response)
        print(f"Enrollment response: {enrollment_response}")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        print(f"Raw response: {response}")
    except Exception as e:
        print(f"❌ Enrollment error: {e}")
        traceback.print_exc()
    
    sock.close()
    print("\n🔚 Debug completed.")

if __name__ == "__main__":
    debug_enrollment_step_by_step()