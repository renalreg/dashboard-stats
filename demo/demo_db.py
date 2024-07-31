import os
import json


def get_db_url():
    # Common config environment variables
    db_driver = os.environ.get("DB_DRIVER", "postgresql+psycopg2")
    db_name = os.getenv("DB_NAME", "UKRDC3")

    # Handle "old" JSON config format
    db_file = os.getenv("JSON_CONF_PATH", None)
    if db_file:
        with open(db_file, "r", encoding="utf-8") as file:
            conf = json.load(file)[db_name]
            return f'{db_driver}://{conf["USER"]}:{conf["PASSWORD"]}@localhost:{conf["DB_PORT"]}/{conf["DATABASE"]}'

    # Handle "new" environment variables
    db_user = os.getenv("DB_USER", "ukrdc3")
    db_pass = os.getenv("DB_PASS", "ukrdc3")
    db_port = os.getenv("DB_PORT", "5432")

    return f"{db_driver}://{db_user}:{db_pass}@localhost:{db_port}/{db_name}"
