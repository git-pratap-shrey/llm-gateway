from typing import Any
from sqlmodel import Field, SQLModel, Session, create_engine, select

from result_store.results_db import Result


class Result_store:
    def __init__(self) -> None:
        self.engine = create_engine("sqlite:///result_db.db")
        SQLModel.metadata.create_all(self.engine)

    def add_to_database(self, payload: dict[str, Any]) -> None:
        with Session(self.engine) as session:
            result = Result(
                job_id=payload["job_id"],
                status=payload["status"],
                output=str(payload.get("output", None)),
                input=str(payload.get("input", None))
            )
            session.add(result)
            session.commit()

    def check_status(self, job_id: str) -> dict[str, Any]:
        with Session(self.engine) as session:
            statement = select(Result).where(Result.job_id == job_id)
            row = session.exec(statement).first()

            if row is None:
                return row

            return row.model_dump()