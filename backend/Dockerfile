FROM python:3.14.7-alpine

WORKDIR /app

COPY . .

EXPOSE 8000

# SCRUM-15 substituirá este comando pelo Gunicorn da aplicação Flask.
CMD ["python", "-m", "http.server", "8000", "--bind", "0.0.0.0"]