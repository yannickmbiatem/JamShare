import grpc
from concurrent import futures
import storage_pb2
import storage_pb2_grpc
import node_pb2
import node_pb2_grpc
import sqlite3
import os
import subprocess
import time
import signal
import sys

class StorageServicer(storage_pb2_grpc.StorageServiceServicer):
    def __init__(self):
        # Database setup
        if not os.path.exists('metadata.db'):
            self.db = sqlite3.connect('metadata.db')
            self.db.execute('CREATE TABLE files (filename TEXT, node_id INT, user_name TEXT, PRIMARY KEY (filename, user_name))')
            self.db.commit()
        else:
            self.db = sqlite3.connect('metadata.db')

        # Node addresses
        self.nodes = {
            1: 'localhost:50052',
            2: 'localhost:50053',
            3: 'localhost:50054',
            4: 'localhost:50055',
            5: 'localhost:50056'
        }
        self.max_per_node = 200 * 1024 * 1024  # 200MB

        # Auto-start the 5 nodes
        self.node_processes = []
        print("Starting 5 storage nodes automatically...")
        for i in range(1, 6):
            cmd = [sys.executable, 'storage_node.py', str(i)]  # Use same Python interpreter
            proc = subprocess.Popen(cmd)
            self.node_processes.append(proc)
            print(f"   → Node {i} started (PID: {proc.pid}) on port {50051 + i}")
            time.sleep(0.5)  # Small delay for clean startup

        print("All 5 nodes are running!\n")

    def choose_node(self, file_size):
        free_spaces = {}
        for node_id, addr in self.nodes.items():
            try:
                with grpc.insecure_channel(addr, options=[('grpc.enable_http_proxy', False)]) as channel:
                    stub = node_pb2_grpc.NodeServiceStub(channel)
                    resp = stub.GetNodeSpace(node_pb2.NodeSpaceRequest(), timeout=5)
                    free = resp.total - resp.used
                    if free >= file_size:
                        free_spaces[node_id] = free
            except Exception:
                pass  # Node might be still starting or down
        if not free_spaces:
            return None
        return max(free_spaces, key=free_spaces.get)  # Choose node with most free space

    # === All other methods remain exactly the same ===
    def UploadFile(self, request, context):
        user = request.token
        filename = request.filename
        content = request.content
        cur = self.db.cursor()
        cur.execute('SELECT * FROM files WHERE filename = ? AND user_name = ?', (filename, user))
        if cur.fetchone():
            return storage_pb2.UploadResponse(success=False, message="File already exists")
        node_id = self.choose_node(len(content))
        if not node_id:
            return storage_pb2.UploadResponse(success=False, message="No space available")
        addr = self.nodes[node_id]
        with grpc.insecure_channel(addr) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            resp = stub.StoreFile(node_pb2.StoreRequest(filename=filename, content=content))
            if resp.success:
                self.db.execute('INSERT INTO files VALUES (?, ?, ?)', (filename, node_id, user))
                self.db.commit()
                return storage_pb2.UploadResponse(success=True, message="File uploaded")
            return storage_pb2.UploadResponse(success=False, message=resp.message)

    def DownloadFile(self, request, context):
        user = request.token
        filename = request.filename
        cur = self.db.cursor()
        cur.execute('SELECT node_id FROM files WHERE filename = ? AND user_name = ?', (filename, user))
        row = cur.fetchone()
        if not row:
            return storage_pb2.DownloadResponse(success=False, content=b'', message="File not found")
        addr = self.nodes[row[0]]
        with grpc.insecure_channel(addr) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            resp = stub.RetrieveFile(node_pb2.RetrieveRequest(filename=filename))
            return storage_pb2.DownloadResponse(success=resp.success, content=resp.content, message=resp.message)

    def DeleteFile(self, request, context):
        user = request.token
        filename = request.filename
        cur = self.db.cursor()
        cur.execute('SELECT node_id FROM files WHERE filename = ? AND user_name = ?', (filename, user))
        row = cur.fetchone()
        if not row:
            return storage_pb2.DeleteResponse(success=False, message="File not found")
        addr = self.nodes[row[0]]
        with grpc.insecure_channel(addr) as channel:
            stub = node_pb2_grpc.NodeServiceStub(channel)
            resp = stub.RemoveFile(node_pb2.RemoveRequest(filename=filename))
        self.db.execute('DELETE FROM files WHERE filename = ? AND user_name = ?', (filename, user))
        self.db.commit()
        return storage_pb2.DeleteResponse(success=resp.success, message="File deleted" if resp.success else resp.message)

    def ListFiles(self, request, context):
        user = request.token
        cur = self.db.cursor()
        cur.execute('SELECT filename FROM files WHERE user_name = ?', (user,))
        filenames = [row[0] for row in cur.fetchall()]
        return storage_pb2.ListResponse(filenames=filenames)

    def GetSpace(self, request, context):
        total = len(self.nodes) * self.max_per_node
        used = 0
        for addr in self.nodes.values():
            try:
                with grpc.insecure_channel(addr) as channel:
                    stub = node_pb2_grpc.NodeServiceStub(channel)
                    resp = stub.GetNodeSpace(node_pb2.NodeSpaceRequest())
                    used += resp.used
            except Exception:
                pass
        return storage_pb2.SpaceResponse(total=total, used=used)


# === Server startup ===
servicer = StorageServicer()  # This triggers auto node start

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
storage_pb2_grpc.add_StorageServiceServicer_to_server(servicer, server)
server.add_insecure_port('[::]:50057')
server.start()
print("Storage master server running on port 50057")
print("Press Ctrl+C to stop everything (master + all nodes)")

def signal_handler(sig, frame):
    print("\nShutting down... terminating all nodes")
    for proc in servicer.node_processes:
        proc.terminate()
        proc.wait()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

server.wait_for_termination()