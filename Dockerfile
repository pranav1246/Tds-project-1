# Use an official Python runtime as a base image
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Overwrite the APT sources with a reliable mirror
RUN echo "deb http://ftp.us.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://ftp.us.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    apt-get update --fix-missing && \
    apt-get install -y nodejs npm bash && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create /data directory if your app expects it
RUN mkdir -p /data

# Copy requirements.txt and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Install Prettier globally via npm (for task A2)
RUN npm install -g prettier@3.4.2

# Copy the rest of your application code into the container
COPY . /app

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Run the FastAPI app using uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
