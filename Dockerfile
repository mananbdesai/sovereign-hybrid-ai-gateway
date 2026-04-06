FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies strictly
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY router.py .

# Expose the API Port
EXPOSE 8000

# Start the FastAPI server using Uvicorn
CMD ["uvicorn", "router:app", "--host", "0.0.0.0", "--port", "8000"]
