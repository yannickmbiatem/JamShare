import socket
import json
import time

def test_enrollment():
    """Test the enrollment process directly"""
    server_host = 'localhost'
    server_port = 8889
    
    print("🔍 Testing enrollment process...")
    
    # Step 1: Login
    print("\n1. Logging in...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    sock.connect((server_host, server_port))
    
    login_data = {
        'type': 'login_account',
        'username': 'yannick',
        'password': 'yann2035'
    }
    
    sock.send(json.dumps(login_data).encode('utf-8'))
    login_response = json.loads(sock.recv(4096).decode('utf-8'))
    
    print(f"Login response: {login_response.get('status')}")
    
    if login_response.get('status') != 'success':
        print(f"❌ Login failed: {login_response.get('message')}")
        sock.close()
        return
    
    session_token = login_response['session_token']
    print(f"✅ Login successful, session token: {session_token[:8]}...")
    
    # Step 2: Enrollment
    print("\n2. Sending enrollment request...")
    enrollment_data = {
        'type': 'enrollment_request',
        'node_id': 'test_node1',
        'session_token': session_token,
        'user_email': 'yannickmbiatem@gmail.com',
        'user_name': 'yannick',
        'cpu_capacity': 4,
        'memory_capacity': 16,
        'storage_capacity': 1.0,  # 1GB
        'bandwidth': 1000
    }
    
    try:
        sock.send(json.dumps(enrollment_data).encode('utf-8'))
        enrollment_response = json.loads(sock.recv(4096).decode('utf-8'))
        print(f"Enrollment response: {enrollment_response}")
        
        if enrollment_response.get('status') == 'enrollment_completed':
            print("✅ Enrollment successful!")
            print(f"Node session token: {enrollment_response['session_token'][:8]}...")
            print(f"Network info: {enrollment_response['network_info']}")
        else:
            print(f"❌ Enrollment failed: {enrollment_response.get('message')}")
            
    except Exception as e:
        print(f"❌ Error during enrollment: {e}")
        import traceback
        traceback.print_exc()
    
    sock.close()
    print("\n🔚 Test completed.")

if __name__ == "__main__":
    test_enrollment()