from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.responses import FileResponse
from sqlalchemy import distinct
from sqlmodel import SQLModel, Field, Session, create_engine

from pydantic import BaseModel
from typing import List, Optional
import json
import uuid
from datetime import datetime
from typing import Tuple

from uuid import UUID
from sqlmodel import select, desc


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


def report_exists(report_id: UUID) -> bool:
    results = session.exec(
        select(BrokenLinkReportData).where(BrokenLinkReportData.report_id == report_id)
    )
    if results.one_or_none() is None:
        return False
    return True


def report_exists_for_date(datestamp: datetime) -> bool:
    results = session.exec(
        select(BrokenLinkReportData).where(BrokenLinkReportData.date == datestamp)
    )
    if results.first() is None:
        return False
    return True


def get_last_report_id_and_datestamp() -> Tuple[UUID, datetime]:
    query = select(BrokenLinkReportData.date, BrokenLinkReportData.report_id).order_by(
        desc(BrokenLinkReportData.date)
    )
    result = session.exec(query).first()
    return result[1], result[0]


class BrokenLink(BaseModel):
    """
    Minimal details about a broken link
    """

    file: str
    url: str
    status_code: int


class BrokenLinkRepo(BaseModel):
    """
    Repo-level information about the broken links
    """

    repo_name: str
    repo_url: str
    broken_links: List[BrokenLink]


class BrokenLinkReport(BaseModel):
    """
    An aggregation of all the data about broken links. The "report"
    """

    report: List[BrokenLinkRepo]
    report_date: datetime
    report_id: Optional[UUID]


class BrokenLinksResponse(BaseModel):
    """
    A report that includes data about newly-broken links, links that were already known to be broken,
    and details about the most recently reported broken link data.
    """

    new_broken_links: List[BrokenLink]
    existing_broken_links: List[BrokenLink]
    last_report_id: UUID
    last_report_date: datetime


class ReportSummary(BaseModel):
    report_id: str
    report_date: datetime


class ReportList(BaseModel):
    reports: List[ReportSummary]


def _get_report_list() -> ReportList:
    query = (
        select(BrokenLinkReportData.date, BrokenLinkReportData.report_id)
        .distinct()
        .order_by(desc(BrokenLinkReportData.date))
    )
    result = session.exec(query).fetchall()
    summary_items = [
        ReportSummary(report_id=str(x[1]), report_date=x[0].isoformat()) for x in result
    ]
    return ReportList(reports=summary_items)


app = FastAPI()

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)
session = Session(engine)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


create_db_and_tables()


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


class DuplicateReportError(Exception):
    pass


def persist(broken_link_report: BrokenLinkReport):
    """
    Persist all the BrokenLinkReportData to the table
    :param broken_link_report:
    :return:
    """

    # if a report already exists with matching datetime, error
    if report_exists_for_date(broken_link_report.report_date):
        raise DuplicateReportError

    # otherwise, persist the data into the table
    report_id = uuid.uuid4()
    result = []
    for repo in broken_link_report.report:
        for link in repo.broken_links:
            result.append(
                create_data(report_id, broken_link_report.report_date, repo, link)
            )

    session.add_all(result)
    session.commit()
    return report_id


def get_report_by_id(report_id: UUID) -> BrokenLinkReport:
    """
    Reconstitute the report from the data in the table
    :param report_id:
    :return:
    """
    query = select(BrokenLinkReportData).where(
        BrokenLinkReportData.report_id == str(report_id)
    )
    result = session.exec(query)
    report_data = result.fetchall()
    report_id = str(report_data[0].report_id)
    report_date = report_data[0].date.isoformat()
    repo_list = [repo.repo_name for repo in report_data]
    broken_link_repos = []
    for repo_name in repo_list:
        # Get all the rows matching the repo name
        rows_for_repo = [row for row in report_data if row.repo_name == repo_name]
        repo_url = rows_for_repo[0].repo_url
        broken_links = []
        for row in rows_for_repo:
            broken_links.append(
                BrokenLink(file=row.file, url=row.url, status_code=row.status_code)
            )
        broken_link_repos.append(
            BrokenLinkRepo(
                repo_name=repo_name, repo_url=repo_url, broken_links=broken_links
            )
        )
    return BrokenLinkReport(
        report_date=report_date,
        report_id=report_id,
        report=broken_link_repos,
    )


@app.post("/report", status_code=201)
def report(broken_link_report: BrokenLinkReport):
    """
    Store new broken link report data.
    :param broken_link_report:
    :return:
    """
    try:
        report_id = persist(broken_link_report)
    except DuplicateReportError as er:
        raise HTTPException(status_code=409, detail=str(er))

    return {"report_id": report_id}


def get_csv_report_by_id(report_id) -> FileResponse:
    blr_json = get_report_by_id(report_id)
    with open("/tmp/json_out.txt", "w") as json_file:
        json.dump(blr_json, json_file)
    return FileResponse("/tmp/json_out.txt")


@app.get("/report/{report_id}")
def get_report(report_id, csv=False):
    """
    Retrieve the data from a specific report.
    :param report_id:
    :param csv:
    :return:
    """
    if csv:
        return get_csv_report_by_id(report_id)
    return get_report_by_id(report_id)


@app.get("/report_summary")
def get_report_list():
    return _get_report_list()


@app.get("/broken_links")
def broken_links():
    return BrokenLinksResponse(
        new_broken_links=[],
        existing_broken_links=[],
        last_report_id=uuid.uuid4(),
        last_report_date=datetime.now(),
    )
