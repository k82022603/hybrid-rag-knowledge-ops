# =============================================================================
# Nginx Stub Service for Hybrid RAG Knowledge Platform
# SCRUM-19: Stub Dockerfile - Health endpoint only
# =============================================================================

FROM nginx:1.25-alpine

# Create simple health check response
RUN mkdir -p /usr/share/nginx/html && \
    echo '{"status":"ok","service":"nginx","version":"stub-1.0"}' > /usr/share/nginx/html/health.json && \
    echo '{"status":"ok","message":"Nginx Stub Service Running"}' > /usr/share/nginx/html/status.json

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/

# Create certs directory (empty for stub)
RUN mkdir -p /etc/nginx/certs

# Expose HTTP and HTTPS ports
EXPOSE 80 443

# Health check endpoint (uses /nginx-health from conf.d/default.conf)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
