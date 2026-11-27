FROM python:3.14.7-slim

WORKDIR /dados
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY csv_read_tool.py db.sql indices.sql *.csv.gz ./
CMD ["python", "-u", "csv_read_tool.py"]
