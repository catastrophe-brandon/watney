from datetime import datetime
from typing import Optional
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
    date: datetime


class BrokenLinkFileData(SQLModel, table=True):
    report_id: UUID = Field(
        default=None, foreign_key="brokenlinkreportdata.report_id", nullable=False
    )
    repo_name: str = Field(default=None, primary_key=True)
    repo_url: str = Field(default=None, primary_key=True)
    file: str = Field(default=None, primary_key=True)
    url: str
    status_code: int


def create_tables(engine: Engine):
    """
    Create the tables in the database
    """
    SQLModel.metadata.create_all(engine)
