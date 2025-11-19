# Dockerfile for Streamlit UI
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["streamlit", "run", "ui.py", "--server.port=8080", "--server.address=0.0.0.0"]