# =============================================================================
# Frontend Stub Service for Hybrid RAG Knowledge Platform
# SCRUM-19: Stub Dockerfile - Simple static page
# =============================================================================

FROM nginx:1.25-alpine

# Create a simple index.html page
RUN mkdir -p /usr/share/nginx/html && \
    cat > /usr/share/nginx/html/index.html << 'EOF'
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Platform - Stub</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 2rem;
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            backdrop-filter: blur(10px);
        }
        h1 { margin-bottom: 0.5rem; }
        .status {
            display: inline-block;
            padding: 0.5rem 1rem;
            background: #4CAF50;
            border-radius: 20px;
            font-size: 0.9rem;
            margin-top: 1rem;
        }
        .info { margin-top: 1rem; opacity: 0.8; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hybrid RAG Knowledge Platform</h1>
        <p>Frontend Stub Service</p>
        <div class="status">Running</div>
        <p class="info">Version: stub-1.0 | Port: 80</p>
    </div>
</body>
</html>
EOF

# Create health endpoint
RUN echo '{"status":"ok","service":"frontend","version":"stub-1.0"}' > /usr/share/nginx/html/health.json

# Copy nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
