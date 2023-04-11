import copy
import json
from random import randint
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

from faker import Faker

fake = Faker()


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
        date=report_date,
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
        repo_list = []
        query = (
            select(BrokenLinkFileData.repo_name, BrokenLinkFileData.repo_url)
            .where(BrokenLinkFileData.report_id == report_id)
            .distinct()
        )
        repo_data = session.exec(query).fetchall()

        broken_link_repos = []
        for repo_name, repo_url in repo_data:
            query = (
                select(BrokenLinkFileData)
                .where(BrokenLinkFileData.report_id == report_id)
                .where(BrokenLinkFileData.repo_name == repo_name)
            )
            broken_links = session.exec(query).fetchall()

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


def broken_links_from_report(report_id: UUID) -> List[BrokenLinkFileData]:
    with get_session() as session:
        query = select(BrokenLinkFileData).where(
            BrokenLinkFileData.report_id == report_id
        )
        return session.exec(query).fetchall()


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
        return broken_links_from_report(new_id), None

    existing_broken = []

    old_report = get_report_by_id(prev_id)
    if len(old_report.report) == 0:
        return None, broken_links_from_report(new_id)

    with get_session() as session:
        prev_query = select(BrokenLinkFileData).where(
            BrokenLinkFileData.report_id == prev_id
        )
        prev_results = session.exec(prev_query).fetchall()
        new_query = select(BrokenLinkFileData).where(
            BrokenLinkFileData.report_id == new_id
        )
        new_results = session.exec(new_query).fetchall()

        # Find all matches in prev_results AND new_results, these are the existing_broken
        for prev_row in prev_results:
            for new_row in new_results:
                if (
                    prev_row.file == new_row.file
                    and prev_row.repo_name == new_row.repo_name
                    and prev_row.repo_url == new_row.repo_url
                ):
                    existing_broken.append(new_row)
                    break

        # Newly broken = all_broken - existing_broken
        newly_broken = copy.deepcopy(new_results)
        for row in existing_broken:
            try:
                newly_broken.remove(row)
            except ValueError:
                pass

    return existing_broken, newly_broken


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


def clone_report(
    existing_report: UUID,
    report_id: UUID,
    timestamp: str,
    add_new_links=False,
    num_new_links=1,
):
    valid_timestamp = datetime.fromisoformat(timestamp)
    with get_session() as session:
        query = select(BrokenLinkFileData).where(
            BrokenLinkFileData.report_id == existing_report
        )
        query_result = session.exec(query).fetchall()
        session.add(BrokenLinkReportData(report_id=report_id, date=valid_timestamp))
        for row in query_result:
            session.add(
                BrokenLinkFileData(
                    report_id=report_id,
                    file=row.file,
                    url=row.url,
                    repo_name=row.repo_name,
                    repo_url=row.repo_url,
                    status_code=row.status_code,
                )
            )
        if add_new_links:
            random_row = query_result[randint(0, len(query_result) - 1)]
            for i in range(0, num_new_links):
                session.add(
                    BrokenLinkFileData(
                        report_id=report_id,
                        file=fake.file_path(),
                        url=random_row.url,
                        repo_name=random_row.repo_name,
                        repo_url=random_row.repo_url,
                        status_code=random_row.status_code,
                    )
                )
        session.commit()
