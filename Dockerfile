FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app.py .
COPY templates/ templates/

# Expose port
EXPOSE 5000

# Run the web server
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "5000"]
