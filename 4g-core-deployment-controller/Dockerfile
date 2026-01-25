# 1. Base image
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy dependency configuration files FIRST
# This avoids reinstalling everything if you only change one line of code
COPY pyproject.toml .

# 4. Install dependencies (without source code yet)
RUN pip install --no-cache-dir . 2>/dev/null || pip install --no-cache-dir build

# 5. NOW copy the source code
# Copy the entire src folder to /app/src
COPY src/ ./src/

# 6. Install the project (now that the code exists)
# This makes "my_project" an importable package
RUN pip install --no-cache-dir .

# 7. Set environment variables
ENV COMPOSE_FILE=/data/compose.yaml
ENV ENV_FILE=/data/.env
ENV API_PORT=8000
ENV LOG_LEVEL=INFO

# 8. Expose port
EXPOSE 8000

# 9. Run the application
CMD ["python", "-m", "4g_core_deployment_controller.main"]