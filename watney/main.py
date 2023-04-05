import uuid
from datetime import datetime

from fastapi import HTTPException
from fastapi import FastAPI

from watney.db.session import get_engine_from_settings
from watney.db.models import create_tables
from watney.errors import DuplicateReportError
from watney.helpers import persist, get_csv_report_by_id, get_report_by_id, \
    get_report_list as get_report_list_, get_last_two_reports, get_report_diff
from watney.schema import BrokenLinkReport, BrokenLinksResponse

app = FastAPI()
create_tables(get_engine_from_settings())


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


@app.get("/report/{report_id}")
async def get_report(report_id, csv=False):
    """
    Retrieve the data from a specific report.
    :param report_id:
    :param csv:
    :return:
    """
    if csv:
        return get_csv_report_by_id(report_id)
    result = get_report_by_id(report_id)
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")


@app.get("/report_summary")
async def get_report_list():
    return get_report_list_()


@app.get("/broken_links")
def broken_links():
    prev_report_id, recent_report_id = get_last_two_reports()
    new_broken_links, existing_broken_links = get_report_diff(prev_report_id, recent_report_id)
    return BrokenLinksResponse(
        new_broken_links=[],
        existing_broken_links=[],
        last_report_id=uuid.uuid4(),
        last_report_date=datetime.now(),
    )
