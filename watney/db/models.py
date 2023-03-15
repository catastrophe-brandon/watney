from datetime import datetime
from uuid import UUID

from sqlalchemy.future import Engine
from sqlmodel import SQLModel, Field


class BrokenLinkReportData(SQLModel, table=True):
    """
    Table that preserves all the report data
    """

    report_id: UUID = Field(default=None, primary_key=True)
    repo_name: str
    repo_url: str
    date: datetime
    file: str
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
