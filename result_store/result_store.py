import os
from pathlib import Path
from typing import Any
from sqlmodel import Field, SQLModel, Session, create_engine, select

from result_store.results_db import Result


class Result_store:
    def __init__(self) -> None:
        db_path = os.getenv("RESULT_DB_PATH", "result_db.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self.engine)

    def create_job(self, job_id: str, input_data: dict[str, Any]) -> None:
        with Session(self.engine) as session:
            result = Result(
                job_id=job_id,
                status="queued",
                data=str(input_data),
                response=None
            )
            session.add(result)
            session.commit()

    def update_job(self, job_id: str, status: str, output: Any) -> None:
        with Session(self.engine) as session:
            statement = select(Result).where(Result.job_id == job_id)
            row = session.exec(statement).first()
            if row:
                row.status = status
                row.response = str(output)
                session.commit()

    def check_status(self, job_id: str) -> dict[str, Any]:
        with Session(self.engine) as session:
            statement = select(Result).where(Result.job_id == job_id)
            row = session.exec(statement).first()

            if row is None:
                return row

            return row.model_dump()