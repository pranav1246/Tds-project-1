# Use an official Node runtime as a parent image (this gives you Node and npm)
FROM node:18-slim

# Install Python3 and pip
RUN apt-get update --fix-missing && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Install Prettier v3.4.2 globally using npm (needed for task A2)
RUN npm install -g prettier@3.4.2

# Copy the rest of your application code into the container
COPY . /app

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Set the command to run the Uvicorn server when the container starts
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
