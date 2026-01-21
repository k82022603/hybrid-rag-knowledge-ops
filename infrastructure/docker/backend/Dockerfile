# =============================================================================
# Backend Stub Service for Hybrid RAG Knowledge Platform
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
Backend Stub Server
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
        if self.path == '/actuator/health':
            self._send_json_response(200, {
                "status": "UP",
                "components": {
                    "db": {"status": "UP"},
                    "diskSpace": {"status": "UP"},
                    "ping": {"status": "UP"},
                    "redis": {"status": "UP"}
                }
            })
        elif self.path == '/actuator/info':
            self._send_json_response(200, {
                "app": {
                    "name": "backend",
                    "version": "stub-1.0",
                    "description": "Backend Stub Service"
                }
            })
        elif self.path == '/':
            self._send_json_response(200, {
                "service": "backend",
                "status": "running",
                "version": "stub-1.0"
            })
        elif self.path.startswith('/api/'):
            self._send_json_response(200, {
                "message": "Backend Stub API",
                "path": self.path,
                "note": "This is a stub response"
            })
        else:
            self._send_json_response(404, {"error": "Not Found", "path": self.path})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"Backend Stub running on port {port}")
    server.serve_forever()
EOF

RUN chmod +x /app/server.py && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8081

# Health check via Spring Actuator endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:8081/actuator/health || exit 1

CMD ["python", "/app/server.py"]
