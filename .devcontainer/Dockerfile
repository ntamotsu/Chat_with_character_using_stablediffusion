# Use the official Python image from the dockerhub
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Set the working directory in docker
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./ .

# Install any dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Specify the command to run on container start
CMD ["streamlit", "run", "app.py"]