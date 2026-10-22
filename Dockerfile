# Every image starts from another one. This one starts from a small Linux system that already has Python 3.14 installed. 
FROM python:3.14-slim

# This creates an /app folder inside the container and moves into it
# Every command after this runs there, a bit like cd /app
WORKDIR /app

# PYTHONDONTWRITEBYTECODE=1 ops Python from creating __pycache__ / .pyc files, which a container doesn't need
# PYTHONUNBUFFERED=1 makes output from print and logs appear immediately. Without it, Python holds output back and docker logs can look empty or delayed.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# These copy your package list into /app and install everything on it. 
# --no-cache-dir tells pip not to keep the downloaded installer files, which keeps the image smaller.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model now, so the app doesn't have to later.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Copy the project code (except what's in .dockerignore).
COPY . .
# The app uses port 8000.
EXPOSE 8000

# On start: update the database tables, then run the server.
CMD ["sh", "-c", "python init_db.py && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]