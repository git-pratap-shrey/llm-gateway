import logging
import os
from contextlib import contextmanager

LOG_DIR = "logging"

@contextmanager
def job_log_file(job_id: str):
    """
    Attaches a FileHandler to the root logger for the duration of a job.
    Ensures all logging.info/error calls are captured in a job-specific file.
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(f"{LOG_DIR}/{job_id}.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))

    root = logging.getLogger()
    root.addHandler(handler)

    try:
        yield
    finally:
        root.removeHandler(handler)
        handler.close()
