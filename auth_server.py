import grpc
from concurrent import futures
import auth_pb2
import auth_pb2_grpc
import sqlite3
import random
import smtplib
from email.mime.text import MIMEText
import os

class AuthServicer(auth_pb2_grpc.AuthServiceServicer):
    def __init__(self):
        if not os.path.exists('users.db'):
            self.db = sqlite3.connect('users.db')
            self.db.execute('CREATE TABLE users (name TEXT PRIMARY KEY, password TEXT, email TEXT)')
            self.db.commit()
        else:
            self.db = sqlite3.connect('users.db')
        self.otps = {}

    def Register(self, request, context):
        try:
            self.db.execute('INSERT INTO users VALUES (?, ?, ?)', (request.name, request.password, request.email))
            self.db.commit()
            return auth_pb2.RegisterResponse(success=True, message="Account created successfully")
        except sqlite3.IntegrityError:
            return auth_pb2.RegisterResponse(success=False, message="Username already exists")

    def Login(self, request, context):
        cur = self.db.cursor()
        cur.execute('SELECT password, email FROM users WHERE name = ?', (request.name,))
        row = cur.fetchone()
        if row and row[0] == request.password:
            otp = str(random.randint(100000, 999999))
            self.otps[request.name] = otp
            msg = MIMEText(f"Your OTP is {otp}")
            msg['Subject'] = 'Login OTP'
            msg['From'] = 'yannickmbiatemtv@gmail.com'  # CHANGE THIS
            msg['To'] = row[1]
            try:
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login('yannickmbiatemtv@gmail.com', 'ajhx xfzk welm hpdj')  # CHANGE THESE
                    server.send_message(msg)
                return auth_pb2.LoginResponse(success=True, message="OTP sent to your email")
            except Exception as e:
                return auth_pb2.LoginResponse(success=False, message=f"Email failed: {str(e)}")
        return auth_pb2.LoginResponse(success=False, message="Invalid username or password")

    def VerifyOTP(self, request, context):
        if request.name in self.otps and self.otps[request.name] == request.otp:
            del self.otps[request.name]
            token = request.name
            return auth_pb2.VerifyOTPResponse(success=True, token=token, message="Login successful")
        return auth_pb2.VerifyOTPResponse(success=False, token="", message="Invalid OTP")

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)
server.add_insecure_port('[::]:50051')
server.start()
print("Auth server running on port 50051")
server.wait_for_termination()