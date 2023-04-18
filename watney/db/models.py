from datetime import datetime
from uuid import UUID

from sqlalchemy.future import Engine
from sqlmodel import SQLModel, Field


class BrokenLinkReportData(SQLModel, table=True):
    report_id: UUID = Field(default=None, primary_key=True)
    date: datetime


class BrokenLinkFileData(SQLModel, table=True):
    report_id: UUID = Field(
        default=None,
        nullable=False,
        primary_key=True,
        foreign_key="brokenlinkreportdata.report_id",
    )
    repo_name: str = Field(default=None, primary_key=True)
    repo_url: str = Field(default=None, primary_key=True)
    file: str = Field(default=None, primary_key=True)
    url: str = Field(default=None, primary_key=True)
    status_code: int


def create_tables(engine: Engine):
    """
    Create the tables in the database
    """
    SQLModel.metadata.create_all(engine)
