# =============================================================================
# AI Service Stub for Hybrid RAG Knowledge Platform
# SCRUM-19: Stub Dockerfile - Health endpoint only (Python HTTP Server)
# =============================================================================

FROM python:3.11-alpine

# Create non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app

# Create health endpoint server
RUN cat > /app/server.py << 'EOF'
#!/usr/bin/env python3
"""
AI Service Stub Server
SCRUM-19: Minimal health endpoint for Docker Compose testing
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def _send_json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        if self.path == '/health':
            self._send_json_response(200, {
                "status": "healthy",
                "service": "ai-service",
                "version": "stub-1.0",
                "components": {
                    "llm": {"status": "ok", "model": "stub"},
                    "vector_store": {"status": "ok"},
                    "graph_store": {"status": "ok"}
                }
            })
        elif self.path == '/':
            self._send_json_response(200, {
                "service": "ai-service",
                "status": "running",
                "version": "stub-1.0",
                "endpoints": ["/health", "/api/v1/search", "/api/v1/query"]
            })
        elif self.path == '/api/v1/search':
            self._send_json_response(200, {
                "message": "AI Service Search Stub",
                "note": "This is a stub response",
                "results": []
            })
        elif self.path == '/api/v1/query':
            self._send_json_response(200, {
                "message": "AI Service Query Stub",
                "note": "This is a stub response",
                "answer": "Stub response - actual AI service not available"
            })
        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'

        if self.path in ['/api/v1/search', '/api/v1/query']:
            self._send_json_response(200, {
                "message": f"AI Service {self.path} Stub",
                "note": "This is a stub response",
                "received": json.loads(body) if body else {}
            })
        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"AI Service Stub running on port {port}")
    server.serve_forever()
EOF

RUN chmod +x /app/server.py && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:8000/health || exit 1

CMD ["python", "/app/server.py"]
