from sqlmodel import Field, SQLModel, create_engine

class Result(SQLModel, table=True):
    job_id: str = Field(primary_key=True)
    data: str | None = None
    status: str
    response: str | None = None

if __name__ == "__main__":
    import os
    db_path = os.getenv("RESULT_DB_PATH", "data/result_db.db")
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)