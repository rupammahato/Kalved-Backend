FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Run app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
