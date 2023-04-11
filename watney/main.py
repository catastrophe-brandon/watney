import uuid
from datetime import datetime

from fastapi import HTTPException
from fastapi import FastAPI

from watney.db.session import get_engine_from_settings
from watney.db.models import create_tables
from watney.errors import DuplicateReportError, NoReportDataError
from watney.helpers import (
    persist,
    get_csv_report_by_id,
    get_report_by_id,
    get_report_list as get_report_list_,
    get_last_two_reports,
    get_report_diff,
    NotEnoughDataError,
)
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
def get_report(report_id, csv=False):
    """
    Retrieve the data from a specific report.
    :param report_id:
    :param csv:
    :return:
    """
    import uuid

    try:
        uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{report_id} is not a valid UUID")
    if csv:
        return get_csv_report_by_id(report_id)
    result = get_report_by_id(report_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return result


@app.get("/report_summary")
async def get_report_list():
    return get_report_list_()


@app.get("/broken_links")
def broken_links():
    try:
        prev_report_id, recent_report_id = get_last_two_reports()
    except NoReportDataError as err:
        raise HTTPException(
            status_code=409,
            detail=f"Not enough report data available to analyze ({err})",
        )
    except NotEnoughDataError as err:
        raise HTTPException(
            status_code=409,
            detail=f"Not enough report data available to analyze ({err})",
        )

    existing_broken_links, new_broken_links = get_report_diff(
        prev_report_id, recent_report_id
    )

    return BrokenLinksResponse(
        new_broken_links=new_broken_links if new_broken_links else [],
        existing_broken_links=existing_broken_links if existing_broken_links else [],
        last_report_id=uuid.uuid4(),
        last_report_date=datetime.now(),
    )
