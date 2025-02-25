import environ
import gzip
import subprocess
from datetime import datetime

env = environ.Env()

environ.Env.read_env(env_file="tacom/.env")
backup_dir = "db_backup"
timestamp_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")

db_config = env.db()
cmd = [
    "pg_dump",
    "-U",
    db_config["USER"],
    "-h",
    db_config["HOST"],
    "-p",
    str(db_config["PORT"]),
    "-d",
    db_config["NAME"],
    db_config["OPTIONS"]["options"],
]


with gzip.open(f"{backup_dir}/backup_{timestamp_str}.gz", "wb") as f:
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)

    for stdout_line in iter(popen.stdout.readline, ""):
        f.write(stdout_line.encode("utf-8"))

        popen.stdout.close()
        popen.wait()
