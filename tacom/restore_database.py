import os
import subprocess
import sys
import environ

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

env = environ.Env()
env.read_env(env_file=f"{SCRIPT_DIR}/tacom/.env")

backup_dir = "db_backup"

if len(sys.argv) != 2:
    print("Usage: python restore_database.py <backup_file.gz>")
    sys.exit(1)

backup_file = sys.argv[1]
backup_path = os.path.join(SCRIPT_DIR, backup_dir, backup_file)

if not os.path.exists(backup_path):
    print(f"Backup file not found: {backup_path}")
    sys.exit(1)

db_config = env.db()
schema_name = db_config["OPTIONS"]["options"].split("=")[1]

env_vars = os.environ.copy()
env_vars["PGPASSWORD"] = db_config["PASSWORD"]


def run_psql_command(sql):
    subprocess.run(
        [
            "psql",
            "-U",
            db_config["USER"],
            "-h",
            db_config["HOST"],
            "-p",
            str(db_config["PORT"]),
            "-d",
            db_config["NAME"],
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            sql,
        ],
        check=True,
        env=env_vars,
        text=True,
    )


# 1. Drop schema if it exists
print(f"Dropping schema '{schema_name}'...")
run_psql_command(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")

# 2. Restore backup (ignore ownership / run as current user)
print(f"Restoring from backup '{backup_file}'...")
with subprocess.Popen(
    [
        "psql",
        "-U",
        db_config["USER"],
        "-h",
        db_config["HOST"],
        "-p",
        str(db_config["PORT"]),
        "-d",
        db_config["NAME"],
        "-v",
        "ON_ERROR_STOP=1",
    ],  # <- ignore role/ownership from dump
    stdin=subprocess.PIPE,
    env=env_vars,
) as psql_proc:
    subprocess.run(["gzip", "-dc", backup_path], stdout=psql_proc.stdin, check=True)
    psql_proc.stdin.close()
    psql_proc.wait()

print("Database schema dropped and backup restored successfully.")
