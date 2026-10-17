import logging
import os
from pathlib import Path
from typing import Any
from sqlmodel import Field, SQLModel, Session, create_engine, select

from result_store.results_db import Result


class Result_store:
    def __init__(self) -> None:
        db_path = os.getenv("RESULT_DB_PATH", "result_db.db")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self.engine)
        logging.debug(f"Result_store: Initialized SQLite engine at '{db_path}'.")

    def create_job(self, job_id: str, input_data: dict[str, Any]) -> None:
        try:
            with Session(self.engine) as session:
                result = Result(
                    job_id=job_id,
                    status="queued",
                    data=str(input_data),
                    response=None
                )
                session.add(result)
                session.commit()
            logging.info(f"Result_store: Created record for job ID {job_id} (status: queued).")
        except Exception as e:
            logging.error(f"Result_store: Failed to create record for job ID {job_id}: {e}")
            raise

    def update_job(self, job_id: str, status: str, output: Any) -> None:
        try:
            with Session(self.engine) as session:
                statement = select(Result).where(Result.job_id == job_id)
                row = session.exec(statement).first()
                if row:
                    row.status = status
                    row.response = str(output)
                    session.commit()
                    logging.info(f"Result_store: Updated job ID {job_id} to status '{status}'.")
                else:
                    logging.warning(f"Result_store: Attempted to update job ID {job_id}, but record was not found.")
        except Exception as e:
            logging.error(f"Result_store: Failed to update job ID {job_id} to status '{status}': {e}")
            raise

    def check_status(self, job_id: str) -> dict[str, Any]:
        try:
            with Session(self.engine) as session:
                statement = select(Result).where(Result.job_id == job_id)
                row = session.exec(statement).first()

                if row is None:
                    logging.info(f"Result_store: Checked status for job ID {job_id} - not found.")
                    return row

                logging.debug(f"Result_store: Checked status for job ID {job_id} - found with status '{row.status}'.")
                return row.model_dump()
        except Exception as e:
            logging.error(f"Result_store: Failed to check status for job ID {job_id}: {e}")
            raise