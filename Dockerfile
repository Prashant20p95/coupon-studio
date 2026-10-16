FROM python:3.11-slim

# Install system libraries needed by OpenCV and PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user according to Hugging Face Spaces standard (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR $HOME/app

# Install Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application source
COPY --chown=user:user . .

# Ensure output directory exists
RUN mkdir -p output_cards

EXPOSE 7860

CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:7860", "app:app", "--timeout", "600"]
