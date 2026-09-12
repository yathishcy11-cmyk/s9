FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.116.1 uvicorn[standard]==0.35.0
COPY main.py .
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","9000"]
