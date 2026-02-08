# syntax=docker/dockerfile:1
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files and npm config
COPY package.json package-lock.json* .npmrc ./

# Install dependencies with BuildKit cache mount for npm cache persistence
# This prevents ETIMEDOUT errors by reusing cached packages across builds
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline --timeout=120000

# Copy source code
COPY . .

# Build the application (uses tsconfig.build.json which excludes test files)
RUN npm run build

# Stage 2: Production
FROM nginx:alpine AS production

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
