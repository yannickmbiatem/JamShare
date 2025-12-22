# JamShare - Your Private Distributed Cloud Storage 🎵💜

**JamShare** is a fully functional, self-hosted distributed cloud storage system built with Python, Flask, gRPC, and SQLite. It combines storage from multiple "nodes" into one seamless private cloud drive — perfect for storing your music, videos, documents, or beats securely on your own machine.

The user sees a single unified storage space (1 GB total from 5 × 200 MB nodes) and never knows about the underlying nodes — just like a real cloud service!

## Features

- **Distributed Storage**: 5 independent storage nodes combine to provide 1 GB total space
- **Unified View**: User interacts with one cloud drive — nodes are completely hidden
- **Large File Support**: Upload files up to ~200 MB (videos, music, etc.)
- **Secure Authentication**: Username/password + OTP via email (2FA-style)
- **Beautiful Music-Themed UI**: Dark purple gradient design with animated sound waves
- **Real-Time Progress Bar**: Smooth AJAX upload with percentage progress
- **Instant Refresh**: Files appear immediately after upload (no page reload needed)
- **Download & Delete**: Full file management
- **Actual Disk Usage**: Files are physically stored in `node_1/` to `node_5/` folders

## Tech Stack

- **Frontend**: Flask + HTML/CSS/JavaScript (AJAX uploads)
- **Backend**: gRPC microservices
  - `auth_server.py` – User registration, login, OTP via email
  - `storage_server.py` – Master coordinator (metadata + node management)
  - `storage_node.py` ×5 – Actual file storage nodes
- **Database**: SQLite (`users.db`, `metadata.db`)
- **Communication**: gRPC with increased message size for large files

## Project Structure
 JamShare/
├── auth.proto                  # gRPC auth service definition
├── storage.proto               # gRPC storage master service
├── node.proto                  # gRPC node service
├── auth_server.py              # Authentication + OTP service
├── storage_server.py           # Master server (auto-starts nodes)
├── storage_node.py             # Node server (run by master)
├── flask_app.py                # Web interface (Flask)
├── metadata.db                 # File location metadata (auto-created)
├── users.db                    # User accounts (auto-created)
├── node_1/ to node_5/          # Actual file storage directories
└── templates/
├── home.html
├── login.html
├── register.html
└── otp.html


## Setup & Run

### 1. Prerequisites
- Python 3.8+
- Install dependencies:
```bash
pip install flask grpcio grpcio-tools


Generate gRPC code
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. auth.proto storage.proto node.proto

Start the system (3 terminals)
Terminal 1 – Auth Server
Bash python auth_server.py
Terminal 2 – Storage Master (auto-starts all 5 nodes)
Bash python storage_server.py
Terminal 3 – Web Interface
Bash python flask_app.py

Open in Browser
Go to: http://localhost:5000

Register a new account
Check your email for OTP
Log in and start uploading!

How It Works

User uploads via web → Flask → gRPC to Storage Master
Master chooses node with most space → forwards file via gRPC
Node saves file physically in its folder
Master records location in metadata.db
All nodes hidden from user — only unified space shown

Stopping the System
Press Ctrl+C in the storage_server.py terminal — it will cleanly shut down all 5 nodes too.
Future