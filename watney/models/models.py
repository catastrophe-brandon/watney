import uuid
from datetime import datetime
from typing import Tuple

from uuid import UUID

from sqlalchemy import desc
from sqlmodel import SQLModel, Field, Session, create_engine, select

from api import BrokenLinkRepo, BrokenLink, BrokenLinkReport

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)
session = Session(engine)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


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
    active: bool


class BrokenLinksData(SQLModel, table=True):
    """
    Stores the latest known broken links.
    """
    file: str
    url: str = Field(default=None, primary_key=True)
    status_code: int


def create_data(
    report_id, report_date: datetime, repo: BrokenLinkRepo, link: BrokenLink
) -> BrokenLinkReportData:
    """
    Take the input data and marshall it into a table row.
    :param report_date:
    :param report_id:
    :param repo:
    :param link:
    :return:
    """
    return BrokenLinkReportData(
        report_id=report_id,
        repo_name=repo.repo_name,
        repo_url=repo.repo_url,
        date=report_date,
        file=link.file,
        url=link.url,
        status_code=link.status_code,
    )


def report_exists(report_id: UUID) -> bool:
    results = session.exec(
        select(BrokenLinkReportData).where(BrokenLinkReportData.report_id == report_id)
    )
    if results.one() is None:
        return False
    return True


def report_exists_for_date(datestamp: datetime) -> bool:
    results = session.exec(
        select(BrokenLinkReportData).where(BrokenLinkReportData.date == datestamp)
    )
    if results.one() is None:
        return False
    return True


def get_last_report_id_and_datestamp() -> Tuple[UUID, datetime]:
    query = select(BrokenLinkReportData.date, BrokenLinkReportData.report_id).order_by(
        desc(BrokenLinkReportData.date)
    )
    result = session.exec(query).first()
    return result[1], result[0]


def persist(broken_link_report: BrokenLinkReport):
    """
    Persist all the BrokenLinkReportData to the table
    :param broken_link_report:
    :return:
    """

    # if a report already exists with matching datetime, error
    if report_exists_for_date(broken_link_report.report_date):
        raise

    # otherwise, persist the data into the table
    report_id = uuid.uuid4()
    result = []
    for repo in broken_link_report.report:
        for link in repo.broken_links:
            result.append(
                create_data(report_id, broken_link_report.report_date, repo, link)
            )

    session.add(result)
    session.commit()
