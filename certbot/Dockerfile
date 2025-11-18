FROM certbot/certbot:latest

# Install docker CLI - try both Alpine and Debian package managers
RUN if command -v apk >/dev/null 2>&1; then \
        apk add --no-cache docker-cli; \
    elif command -v apt-get >/dev/null 2>&1; then \
        apt-get update && \
        apt-get install -y -qq docker.io && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        echo "Warning: Could not determine package manager"; \
    fi

# Keep the original entrypoint
ENTRYPOINT []
