FROM python:3.12-slim

WORKDIR /app

# Install git and curl for system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and agency agents
COPY . .

# Expose enterprise server port
EXPOSE 8585

# Launch the autonomous enterprise
CMD ["python3", "app.py", "--host", "0.0.0.0", "--port", "8585"]
