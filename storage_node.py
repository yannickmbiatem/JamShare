import os
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: python storage_node.py <node_id 1-5>")
        sys.exit(1)
    
    try:
        node_id = int(sys.argv[1])
    except ValueError:
        print("Node ID must be an integer")
        sys.exit(1)
    
    if node_id < 1 or node_id > 5:
        print("Node ID must be between 1 and 5")
        sys.exit(1)

    import grpc
    from concurrent import futures
    import node_pb2
    import node_pb2_grpc

    class NodeServicer(node_pb2_grpc.NodeServiceServicer):
        def __init__(self, node_id):
            self.node_id = node_id
            self.dir = f'node_{node_id}'
            os.makedirs(self.dir, exist_ok=True)
            self.max_size = 200 * 1024 * 1024

        def get_used_size(self):
            total = 0
            for root, _, files in os.walk(self.dir):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.path.isfile(fp):
                        total += os.path.getsize(fp)
            return total

        def StoreFile(self, request, context):
            if self.get_used_size() + len(request.content) > self.max_size:
                return node_pb2.StoreResponse(success=False, message="No space on node")
            path = os.path.join(self.dir, request.filename)
            try:
                with open(path, 'wb') as f:
                    f.write(request.content)
                return node_pb2.StoreResponse(success=True, message="Stored")
            except Exception as e:
                return node_pb2.StoreResponse(success=False, message=str(e))

        def RetrieveFile(self, request, context):
            path = os.path.join(self.dir, request.filename)
            if os.path.exists(path) and os.path.isfile(path):
                try:
                    with open(path, 'rb') as f:
                        content = f.read()
                    return node_pb2.RetrieveResponse(success=True, content=content, message="")
                except:
                    return node_pb2.RetrieveResponse(success=False, content=b'', message="Read error")
            return node_pb2.RetrieveResponse(success=False, content=b'', message="File not found")

        def RemoveFile(self, request, context):
            path = os.path.join(self.dir, request.filename)
            if os.path.exists(path) and os.path.isfile(path):
                try:
                    os.remove(path)
                    return node_pb2.RemoveResponse(success=True, message="Removed")
                except:
                    return node_pb2.RemoveResponse(success=False, message="Delete error")
            return node_pb2.RemoveResponse(success=False, message="Not found")

        def GetNodeSpace(self, request, context):
            used = self.get_used_size()
            return node_pb2.NodeSpaceResponse(total=self.max_size, used=used)

    GRPC_OPTIONS = [
        ('grpc.max_send_message_length', 200 * 1024 * 1024),
        ('grpc.max_receive_message_length', 200 * 1024 * 1024)
    ]

    port = 50051 + node_id
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), options=GRPC_OPTIONS)
    node_pb2_grpc.add_NodeServiceServicer_to_server(NodeServicer(node_id), server)
    server.add_insecure_port(f'[::]:{port}')
    print(f"Node {node_id} running on port {port} - directory: node_{node_id}/")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    main()