import smtplib
import hashlib
import secrets
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os

class UTPService:
    """University Transfer Protocol Authentication Service"""
    
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587, 
                 email_sender=None, email_password=None, enable_email=True):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_sender = email_sender
        self.email_password = email_password
        self.enable_email = enable_email
        self.pending_auth = {}
        self.auth_tokens = {}
        
    def generate_verification_code(self, length=8):
        """Generate a secure verification code"""
        return ''.join(secrets.choice('0123456789') for _ in range(length))
    
    def send_verification_email(self, user_email, user_name, node_id):
        """Send UTP verification email"""
        verification_code = self.generate_verification_code()
        auth_token = secrets.token_hex(16)
        
        # Store pending authentication
        self.pending_auth[auth_token] = {
            'email': user_email,
            'code': verification_code,
            'node_id': node_id,
            'timestamp': time.time(),
            'verified': False
        }
        
        # If email is disabled or not configured, just show the code
        if not self.enable_email or not self.email_sender or not self.email_password:
            print(f"📧 Email service disabled. Verification code for {user_email}: {verification_code}")
            return auth_token
        
        # Email content
        subject = "UTP Authentication - Cloud Storage Network"
        body = f"""
        Dear {user_name},
        
        Your UTP verification code for node {node_id} is: {verification_code}
        
        This code will expire in 15 minutes.
        
        Cloud Storage Network Authentication System
        """
        
        # Send email
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = user_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            
            print(f"📧 UTP verification email sent to {user_email}")
            return auth_token
            
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            print(f"🔐 Verification Code (fallback): {verification_code}")
            return auth_token
    
    def verify_code(self, auth_token, verification_code):
        """Verify the UTP code"""
        if auth_token not in self.pending_auth:
            return False, "Invalid authentication token"
        
        auth_data = self.pending_auth[auth_token]
        
        # Check expiration (15 minutes)
        if time.time() - auth_data['timestamp'] > 900:
            del self.pending_auth[auth_token]
            return False, "Verification code expired"
        
        # Verify code
        if auth_data['code'] == verification_code:
            auth_data['verified'] = True
            # Generate session token
            session_token = secrets.token_hex(32)
            self.auth_tokens[session_token] = {
                'node_id': auth_data['node_id'],
                'email': auth_data['email'],
                'created_at': time.time()
            }
            # Clean up pending auth
            del self.pending_auth[auth_token]
            return True, session_token
        else:
            return False, "Invalid verification code"
    
    def validate_session(self, session_token):
        """Validate session token"""
        if session_token not in self.auth_tokens:
            return False, None
        
        session_data = self.auth_tokens[session_token]
        # Session valid for 24 hours
        if time.time() - session_data['created_at'] > 86400:
            del self.auth_tokens[session_token]
            return False, None
        
        return True, session_data

class AuthenticationServer:
    """Main authentication server that integrates with cloud storage"""
    
    def __init__(self, email_sender=None, email_password=None, enable_email=True):
        self.utp_service = UTPService(
            email_sender=email_sender,
            email_password=email_password,
            enable_email=enable_email
        )
        self.enrolled_nodes = {}
        
    def start_enrollment(self, node_id, user_email, user_name):
        """Start the UTP enrollment process"""
        print(f"🔐 Starting UTP enrollment for node {node_id}")
        auth_token = self.utp_service.send_verification_email(user_email, user_name, node_id)
        return auth_token
    
    def complete_enrollment(self, auth_token, verification_code):
        """Complete the enrollment process"""
        success, result = self.utp_service.verify_code(auth_token, verification_code)
        
        if success:
            session_token = result
            session_data = self.utp_service.auth_tokens[session_token]
            node_id = session_data['node_id']
            
            self.enrolled_nodes[node_id] = {
                'session_token': session_token,
                'email': session_data['email'],
                'enrolled_at': time.time(),
                'status': 'active'
            }
            
            print(f"✅ UTP enrollment completed for node {node_id}")
            return True, session_token
        else:
            return False, result
    
    def validate_node_access(self, node_id, session_token):
        """Validate if node can access cloud services"""
        if node_id not in self.enrolled_nodes:
            return False, "Node not enrolled"
        
        node_data = self.enrolled_nodes[node_id]
        if node_data['session_token'] != session_token:
            return False, "Invalid session token"
        
        valid, session_data = self.utp_service.validate_session(session_token)
        if not valid:
            return False, "Session expired"
        
        return True, "Access granted"

class EnrollmentProtocol:
    """Protocol definitions for enrollment service communication"""
    
    @staticmethod
    def create_enrollment_request(node_id, user_email, user_name):
        return {
            'type': 'enrollment_request',
            'node_id': node_id,
            'user_email': user_email,
            'user_name': user_name,
            'timestamp': time.time()
        }
    
    @staticmethod
    def create_verification_request(auth_token, verification_code):
        return {
            'type': 'verification_request',
            'auth_token': auth_token,
            'verification_code': verification_code,
            'timestamp': time.time()
        }
    
    @staticmethod
    def create_access_check(node_id, session_token):
        return {
            'type': 'access_check',
            'node_id': node_id,
            'session_token': session_token,
            'timestamp': time.time()
        }