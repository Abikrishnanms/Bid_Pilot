FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for pdfplumber and other ML tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip to support modern wheel metadata standards
RUN pip install --no-cache-dir --upgrade pip

# Install lightweight CPU-only PyTorch (~180MB instead of ~4GB with CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt


COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
