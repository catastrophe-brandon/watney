from typing import List

import pytest
import datetime
import uuid

from sqlalchemy.orm.exc import ObjectDeletedError

from watney.db.models import BrokenLinkReportData, create_tables
from watney.db.session import get_session, get_engine_from_settings
from watney.helpers import create_data, clear_db
from watney.schema import BrokenLink, BrokenLinkRepo

from faker import Faker

fake = Faker()

FAKE_REPORT_DATE = datetime.datetime.fromisoformat("2023-03-14T14:15:34.726727")
FAKE_REPORT_UUID = uuid.uuid4()


def create_fake_link_data(url) -> List[BrokenLink]:
    result = []
    for i in range(0, 10):
        file_path = fake.file_path()
        result.append(BrokenLink(file=file_path, url=url + file_path, status_code=404))
    return result


def create_fake_repo() -> BrokenLinkRepo:
    url = fake.url()
    return BrokenLinkRepo(
        repo_name=fake.domain_word(),
        repo_url=url,
        broken_links=create_fake_link_data(url),
    )


def create_fake_repos() -> List[BrokenLinkRepo]:
    result = []
    for i in range(0, 20):
        result.append(create_fake_repo())
    return result


def create_fake_report(
    report_id: uuid.UUID, report_ts: datetime
) -> BrokenLinkReportData:
    """
    Models and persists fake report data to the db.
    :param report_id:
    :param report_ts:
    :return:
    """
    fake_repos = create_fake_repos()
    blrd = None
    report_data_list = []
    with get_session() as session:
        # for each link in each repo we need to create a row
        report_data = None
        for fake_repo in fake_repos:
            for broken_link in fake_repo.broken_links:
                broken_link_data = BrokenLink(
                    file=broken_link.file,
                    url=broken_link.url,
                    status_code=broken_link.status_code,
                )
                last_report_data = report_data
                report_data = create_data(
                    report_id=report_id,
                    report_date=report_ts,
                    repo=fake_repo,
                    link=broken_link_data,
                )
                if last_report_data == report_data:
                    raise
            blrd = report_data
            report_data_list.append(report_data)
            session.add(report_data)
        session.commit()
    return blrd


def delete_report_data(broken_link_report_data: List[BrokenLinkReportData]):
    with get_session() as session:
        for blrd in broken_link_report_data:
            session.delete(blrd)
        session.commit()


@pytest.fixture
def fake_report():
    create_tables(get_engine_from_settings())
    clear_db()
    report_data = create_fake_report(FAKE_REPORT_UUID, FAKE_REPORT_DATE)
    yield FAKE_REPORT_UUID
    try:
        delete_report_data([report_data])
    except ObjectDeletedError:
        pass


@pytest.fixture
def multiple_reports():
    last_id = None
    last_date = None
    all_data = []
    for i in range(0, 100):
        last_id = uuid.uuid4()
        last_date = datetime.datetime.utcnow()
        all_data.append(create_fake_report(last_id, last_date))
    yield last_id, last_date
    delete_report_data(all_data)


@pytest.fixture
def empty_db():
    create_tables(get_engine_from_settings())
    clear_db()
