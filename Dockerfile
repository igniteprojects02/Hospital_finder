# app/Dockerfile
FROM python:3.11.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# Combine commands into a single CMD
CMD ["sh", "-c", "python3.11 flask run 0.0.0.0:8001"]
