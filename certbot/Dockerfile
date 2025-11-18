FROM certbot/certbot:latest

# Install docker CLI
RUN apt-get update && \
    apt-get install -y -qq docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Keep the original entrypoint
ENTRYPOINT []
