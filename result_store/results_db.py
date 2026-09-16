from sqlmodel import Field, SQLModel, create_engine

class Result(SQLModel, table=True):
    job_id: str = Field(primary_key=True)
    data: str | None = None

if __name__ == "__main__":
    engine = create_engine("sqlite:///result_db.db")
    SQLModel.metadata.create_all(engine)