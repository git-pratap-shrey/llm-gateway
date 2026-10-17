import logging
import os
from contextlib import contextmanager

LOG_DIR = os.getenv("LOG_DIR", "/logging" if os.path.exists("/logging") else "logging")

@contextmanager
def job_log_file(job_id: str):
    """
    Attaches a FileHandler to the root logger for the duration of a job.
    Ensures all logging.info/error calls are captured in a job-specific file.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = f"{LOG_DIR}/{job_id}.log"
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.addHandler(handler)
    logging.debug(f"Attached per-job log file for job ID {job_id} at {log_path}.")

    try:
        yield
    finally:
        logging.debug(f"Detaching per-job log file for job ID {job_id}.")
        root.removeHandler(handler)
        handler.close()
