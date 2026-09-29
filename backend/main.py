import os

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

app = Flask(__name__)

db_user = os.getenv("DB_USER", "spi")
db_password = os.getenv("DB_PASSWORD", "spi")
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME", "spi")

db_string = (
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

app.config["DB_URL"] = db_string


def get_db_connection():
    return psycopg.connect(db_string, connect_timeout=5)


@app.get("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "backend",
        "database_url": db_string,
    })


@app.get("/health")
def health():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as exc:
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(exc),
        }), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)