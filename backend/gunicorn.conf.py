import os

# Configuração de rede
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Concorrência: workers (processos) e threads por worker
# O modelo 'gthread' permite atender múltiplas requisições simultâneas com I/O concorrente
workers = int(os.getenv("GUNICORN_WORKERS", "4"))
threads = int(os.getenv("GUNICORN_THREADS", "8"))
worker_class = "gthread"

# Tamanho da fila de conexões pendentes no socket TCP do SO
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "2"))

# Logs
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
