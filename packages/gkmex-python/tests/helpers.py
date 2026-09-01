import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread


def read_body(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    return handler.rfile.read(length)


def _send(handler, status, media_type, payload):
    handler.send_response(status)
    handler.send_header("Content-Type", media_type)
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def send_json(handler, status, payload):
    _send(
        handler,
        status,
        "application/json; charset=utf-8",
        json.dumps(payload).encode("utf-8"),
    )


def send_sse(handler, payload):
    _send(
        handler,
        200,
        "text/event-stream; charset=utf-8",
        payload.encode("utf-8"),
    )


def send_bytes(handler, status, media_type, payload):
    _send(handler, status, media_type, payload)


@contextmanager
def serve(route):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route(self, requests)

        def do_POST(self):
            route(self, requests)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}", requests
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
