from flask import Flask, request, render_template, session, redirect, send_file
import io
import grpc
import auth_pb2
import auth_pb2_grpc
import storage_pb2
import storage_pb2_grpc

app = Flask(__name__)
app.secret_key = 'change_this_to_a_strong_secret_key_in_production'

AUTH_ADDR = 'localhost:50051'
STORAGE_ADDR = 'localhost:50057'

# gRPC options for large files (200MB limit)
GRPC_OPTIONS = [
    ('grpc.max_send_message_length', 200 * 1024 * 1024),
    ('grpc.max_receive_message_length', 200 * 1024 * 1024)
]

@app.route('/', methods=['GET'])
def home():
    if 'token' not in session:
        return redirect('/login')
    with grpc.insecure_channel(STORAGE_ADDR, options=GRPC_OPTIONS) as channel:
        stub = storage_pb2_grpc.StorageServiceStub(channel)
        space_resp = stub.GetSpace(storage_pb2.SpaceRequest(token=session['token']))
        total_mb = space_resp.total / (1024 * 1024)
        used_mb = space_resp.used / (1024 * 1024)
        available = f"Available: {total_mb - used_mb:.2f} MB / {total_mb:.2f} MB"
        list_resp = stub.ListFiles(storage_pb2.ListRequest(token=session['token']))
        files = list_resp.filenames
    return render_template('home.html', space=available, files=files)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        email = request.form['email']
        with grpc.insecure_channel(AUTH_ADDR) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            resp = stub.Register(auth_pb2.RegisterRequest(name=name, password=password, email=email))
        if resp.success:
            return redirect('/login')
        return render_template('register.html', message=resp.message)
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        with grpc.insecure_channel(AUTH_ADDR) as channel:
            stub = auth_pb2_grpc.AuthServiceStub(channel)
            resp = stub.Login(auth_pb2.LoginRequest(name=name, password=password))
        if resp.success:
            session['name'] = name
            return render_template('otp.html')
        return render_template('login.html', message=resp.message)
    return render_template('login.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    otp = request.form['otp']
    name = session.get('name')
    if not name:
        return "Error", 400
    with grpc.insecure_channel(AUTH_ADDR) as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        resp = stub.VerifyOTP(auth_pb2.VerifyOTPRequest(name=name, otp=otp))
    if resp.success:
        session['token'] = resp.token
        return redirect('/')
    return render_template('otp.html', message=resp.message)

@app.route('/upload', methods=['POST'])
def upload():
    if 'token' not in session:
        return "Login required", 401

    if 'file' not in request.files:
        return "No file selected", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    content = file.read()
    if len(content) == 0:
        return "Empty file", 400

    try:
        with grpc.insecure_channel(STORAGE_ADDR, options=GRPC_OPTIONS) as channel:
            stub = storage_pb2_grpc.StorageServiceStub(channel)
            resp = stub.UploadFile(storage_pb2.UploadRequest(
                filename=file.filename,
                content=content,
                token=session['token']
            ), timeout=60)
            if resp.success:
                return '', 200
            else:
                return resp.message, 400
    except grpc.RpcError as e:
        return f"Storage error: {e.details()}", 500
    except Exception as e:
        return f"Server error: {str(e)}", 500

@app.route('/download/<filename>')
def download(filename):
    if 'token' not in session:
        return "Login required", 401
    with grpc.insecure_channel(STORAGE_ADDR, options=GRPC_OPTIONS) as channel:
        stub = storage_pb2_grpc.StorageServiceStub(channel)
        resp = stub.DownloadFile(storage_pb2.DownloadRequest(filename=filename, token=session['token']))
    if resp.success:
        return send_file(io.BytesIO(resp.content), as_attachment=True, download_name=filename)
    return resp.message, 404

@app.route('/delete/<filename>')
def delete(filename):
    if 'token' not in session:
        return "Login required", 401
    with grpc.insecure_channel(STORAGE_ADDR, options=GRPC_OPTIONS) as channel:
        stub = storage_pb2_grpc.StorageServiceStub(channel)
        resp = stub.DeleteFile(storage_pb2.DeleteRequest(filename=filename, token=session['token']))
    return redirect('/') if resp.success else (resp.message, 400)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True, port=5000)