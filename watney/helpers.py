import json
from uuid import UUID, uuid4
from datetime import datetime
from typing import Tuple, List, Optional

from fastapi.responses import FileResponse
from sqlmodel import select, desc

from watney.db.session import get_session
from watney.db.models import BrokenLinkReportData, BrokenLinkFileData
from watney.errors import DuplicateReportError, NoReportDataError
from watney.schema import (
    BrokenLink,
    BrokenLinkRepo,
    BrokenLinkReport,
    ReportList,
    ReportSummary,
)


def report_exists(report_id: UUID) -> bool:
    results = get_session().exec(
        select(BrokenLinkReportData)
        .where(BrokenLinkReportData.report_id == report_id)
        .limit(1)
    )
    if results.one_or_none() is None:
        return False
    return True


def report_exists_for_date(datestamp: datetime) -> bool:
    results = get_session().exec(
        select(BrokenLinkReportData)
        .where(BrokenLinkReportData.date == datestamp)
        .limit(1)
    )
    if results.first() is None:
        return False
    return True


def get_last_report_id_and_datestamp() -> Tuple[UUID, datetime]:
    query = select(BrokenLinkReportData.date, BrokenLinkReportData.report_id).order_by(
        desc(BrokenLinkReportData.date)
    )
    result: tuple[datetime, UUID] = get_session().exec(query).first()
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
    report_id, report_date: datetime, repo: BrokenLinkRepo, link: Optional[BrokenLink]
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
        # repo_name=repo.repo_name,
        # repo_url=repo.repo_url,
        date=report_date,
        # file=link.file if link else None,
        # url=link.url if link else None,
        # status_code=link.status_code if link else None,
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

    # Create the report row
    blrd = BrokenLinkReportData(
        report_id=report_id, date=broken_link_report.report_date
    )
    # Create the data rows
    for repo in broken_link_report.report:
        for link in repo.broken_links:
            result.append(
                BrokenLinkFileData(
                    report_id=report_id,
                    repo_name=repo.repo_name,
                    repo_url=repo.repo_url,
                    file=link.file,
                    url=link.url,
                    status_code=link.status_code,
                )
            )

    with get_session() as session:
        session.add(blrd)
        session.add_all(result)
        session.commit()
    return report_id


def get_report_by_id(id_: UUID) -> Optional[BrokenLinkReport]:
    """
    Reconstitute the report from the data in the table
    :param id_:
    :return:
    """
    query = (
        select(BrokenLinkReportData)
        .where(BrokenLinkReportData.report_id == str(id_))
        .order_by(BrokenLinkReportData.date)
    )

    with get_session() as session:
        result = session.exec(query)
        report_data = result.fetchall()
        if len(report_data) == 0:
            return None
        report_id = id_
        report_date = report_data[0].date.isoformat()

        query = (
            select(BrokenLinkFileData)
            .where(BrokenLinkFileData.report_id == str(id_))
            .order_by(BrokenLinkFileData.repo_name)
        )
        result = session.exec(query)
        row_data = result.fetchall()
        if len(row_data) == 0:
            # Report exists, but there are no broken links
            return BrokenLinkReport(
                report_date=report_date, report_id=report_id, report=[]
            )

        # Build a list of all the repo names
        repo_list = [repo.repo_name for repo in row_data]
        broken_link_repos = []

        for repo_name in repo_list:
            # Get all the rows matching the repo name
            rows_for_repo = [row for row in row_data if row.repo_name == repo_name]
            repo_url = rows_for_repo[0].repo_url
            broken_links = []
            for row in rows_for_repo:
                broken_links.append(
                    BrokenLink(
                        file=row.file,
                        url=repo_url + row.file,
                        status_code=row.status_code,
                    )
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


class NotEnoughDataError(Exception):
    pass


def get_last_two_reports() -> Optional[Tuple[UUID, UUID]]:
    """
    Gets the report ids of the most recent two reports
    :return:
    """
    query = (
        select(BrokenLinkReportData.report_id, BrokenLinkReportData.date)
        .order_by(desc(BrokenLinkReportData.date))
        .limit(2)
    )
    result = get_session().exec(query)
    last_two = result.fetchall()
    if len(last_two) < 2:
        raise NotEnoughDataError

    return last_two[1][0], last_two[0][0]


def get_report_diff(
    prev_id: UUID, new_id: UUID
) -> (List[BrokenLink], List[BrokenLink]):
    """
    Compare two reports and return the list of newly broken links and the list of known/existing
    broken links.
    :return:
    """
    if new_id is None:
        # No report data in the database
        raise NoReportDataError

    if prev_id is None:
        # no previous report data exists
        cur_report = get_report_by_id(new_id)
        newly_broken = []
        for repo in cur_report.report:
            newly_broken.extend(repo.broken_links)
        return newly_broken, None

    existing_broken = []
    new_broken = []

    old_report = get_report_by_id(prev_id)
    if len(old_report.report) == 0:
        # No broken links in old report, return only new broken links
        cur_report = get_report_by_id(new_id)
        newly_broken = []
        for repo in cur_report.report:
            newly_broken.extend(repo.broken_links)
        return newly_broken, None

    new_report = get_report_by_id(new_id)

    # walk through the old report row-by-row to compare the broken links with the new report
    for old_repo in old_report.report:
        for new_repo in new_report.report:
            # If repo names match, search for the link in the repo record
            if new_repo.repo_name == old_repo.repo_name:
                pass
                # if the link exists in the new report, add it to the list of known/existing broken
                # if new_repo.
                # if the link does not exist in the broken report, it was probably fixed recently
    return existing_broken, new_broken


def clear_db():
    """
    Exactly what it sounds like. Nukes all the data. Primarily intended for usage during testing.
    :return:
    """
    with get_session() as session:
        query = select(BrokenLinkReportData)
        result = get_session().exec(query)
        for row in result:
            session.delete(row)
        query = select(BrokenLinkFileData)
        result = get_session().exec(query)
        for row in result:
            session.delete(row)
        session.commit()


def delete_report_data(report_id: UUID):
    """
    Delete all data for the report with the matching UUID
    :param report_id:
    :return:
    """
    with get_session() as session:
        query = select(BrokenLinkFileData).where(
            BrokenLinkFileData.report_id == report_id
        )
        query_result = session.exec(query)
        for row in query_result:
            session.delete(row)
        query = select(BrokenLinkReportData).where(
            BrokenLinkReportData.report_id == report_id
        )
        session.delete(session.exec(query).first())
        session.commit()
