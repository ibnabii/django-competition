import environ
import gzip
import subprocess
import os
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
    "-n",
    db_config["OPTIONS"]["options"].split("=")[1],
]

os.environ["PGPASSWORD"] = db_config["PASSWORD"]


with gzip.open(f"{backup_dir}/backup_{timestamp_str}.gz", "wb") as f:
    popen = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )

    # Iterate over stdout until the process finishes
    for stdout_line in iter(popen.stdout.readline, ""):
        if stdout_line:
            f.write(stdout_line.encode("utf-8"))

    # Close the stdout after reading
    popen.stdout.close()
    popen.wait()  # Ensure the process finishes
