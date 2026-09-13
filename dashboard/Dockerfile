FROM nginxinc/nginx-unprivileged:1.27-alpine-slim

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy pre-built static assets
COPY dist /usr/share/nginx/html

# Expose non-root port
EXPOSE 8080

# Immutable read-only healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1:8080/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
