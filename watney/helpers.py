import json
from uuid import UUID, uuid4
from datetime import datetime
from typing import Tuple

from fastapi.responses import FileResponse
from sqlmodel import select, desc

from watney.db.session import get_session
from watney.db.models import BrokenLinkReportData
from watney.errors import DuplicateReportError
from watney.schema import BrokenLink, BrokenLinkRepo, BrokenLinkReport, ReportList, ReportSummary


def report_exists(report_id: UUID) -> bool:
    results = get_session().exec(
        select(BrokenLinkReportData).where(BrokenLinkReportData.report_id == report_id)
    )
    if results.one_or_none() is None:
        return False
    return True


def report_exists_for_date(datestamp: datetime) -> bool:
    results = get_session().exec(
        select(BrokenLinkReportData).where(BrokenLinkReportData.date == datestamp)
    )
    if results.first() is None:
        return False
    return True


def get_last_report_id_and_datestamp() -> Tuple[UUID, datetime]:
    query = select(BrokenLinkReportData.date, BrokenLinkReportData.report_id).order_by(
        desc(BrokenLinkReportData.date)
    )
    result = get_session().exec(query).first()
    return result[1], result[0]


def get_report_list() -> ReportList:
    query = (
        select(BrokenLinkReportData.date, BrokenLinkReportData.report_id)
        .distinct()
        .order_by(desc(BrokenLinkReportData.date))
    )
    result = get_session().exec(query).fetchall()
    summary_items = [
        ReportSummary(report_id=str(x[1]), report_date=x[0].isoformat()) for x in result
    ]
    return ReportList(reports=summary_items)


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
    report_id = uuid4()
    result = []
    for repo in broken_link_report.report:
        for link in repo.broken_links:
            result.append(
                create_data(report_id, broken_link_report.report_date, repo, link)
            )

    session = get_session()
    session.add_all(result)
    session.commit()
    return report_id


def get_report_by_id(id_: UUID) -> BrokenLinkReport:
    """
    Reconstitute the report from the data in the table
    :param report_id:
    :return:
    """
    query = select(BrokenLinkReportData).where(
        BrokenLinkReportData.report_id == str(id_)
    )
    result = get_session().exec(query)
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


def get_csv_report_by_id(report_id) -> FileResponse:
    blr_json = get_report_by_id(report_id)
    with open("/tmp/json_out.txt", "w") as json_file:
        json.dump(blr_json, json_file)
    return FileResponse("/tmp/json_out.txt")
