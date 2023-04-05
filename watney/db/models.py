from datetime import datetime
from uuid import UUID

from sqlalchemy.future import Engine
from sqlmodel import SQLModel, Field


class BrokenLinkReportData(SQLModel, table=True):
    """
    Table that preserves all the report data.
    Notes:
        Data here is denormalized for the sake of hacking something together.
        The primary key declarations exists solely to satisfy the ORM.
    """

    report_id: UUID = Field(default=None, primary_key=True)
    repo_name: str = Field(default=None, primary_key=True)
    repo_url: str
    date: datetime = Field(default=None, primary_key=True)
    file: str = Field(default=None, primary_key=True)
    url: str
    status_code: int


class BrokenLinksData(SQLModel, table=True):
    """
    Stores the latest known broken links.
    """

    file: str
    url: str = Field(default=None, primary_key=True)
    status_code: int


def create_tables(engine: Engine):
    """
    Create the tables in the database
    """
    SQLModel.metadata.create_all(engine)
