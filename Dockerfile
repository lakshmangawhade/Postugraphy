# Stage 1: Use an official Python runtime as a parent image.
# The 'slim' version is smaller and good for production.
FROM python:3.9-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Copy the requirements file into the container.
# This is done as a separate step to leverage Docker's layer caching.
# Dependencies will only be reinstalled if this file changes.
COPY requirements.txt .

# Install Gunicorn (a production-grade WSGI server for Python) and other dependencies.
# --no-cache-dir reduces the image size by not storing the download cache.
RUN pip install --no-cache-dir gunicorn && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's source code into the container.
COPY . .

# Expose port 5000 to the outside world. This is the port Gunicorn will listen on.
EXPOSE 5000

# Define the command to run the application when the container starts.
# We use Gunicorn to serve the Flask app ('app' instance inside the 'main.py' file).
# --bind 0.0.0.0:5000 makes the server accessible from outside the container.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]