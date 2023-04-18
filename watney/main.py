import uuid
from datetime import datetime

from fastapi import HTTPException
from fastapi import FastAPI
from starlette.responses import FileResponse

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


@app.get("/report-summary")
async def get_report_list():
    return get_report_list_()


@app.get("/broken-links")
def broken_links(csv: bool = False):
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

    if csv:
        import csv

        file_path = "/tmp/export.csv"
        with open(file_path, "w", newline="") as csvfile:
            data_writer = csv.writer(
                csvfile, delimiter=" ", quotechar="|", quoting=csv.QUOTE_MINIMAL
            )
            # headers
            data_writer.writerow(
                ["repo name", "repo url", "file path", "full url", "status code", "new or existing"]
            )
            # data
            for link in existing_broken_links:
                data_writer.writerow(
                    [link.repo_name, link.repo_url, link.file, link.url, link.status_code, "existing/known"]
                )
            for link in new_broken_links:
                data_writer.writerow([link.repo_name, link.repo_url, link.file, link.url, link.status_code, "new"])
        response = FileResponse(file_path, media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=export.csv"
        return response
    else:
        return BrokenLinksResponse(
            new_broken_links=new_broken_links if new_broken_links else [],
            existing_broken_links=existing_broken_links
            if existing_broken_links
            else [],
            last_report_id=uuid.uuid4(),
            last_report_date=datetime.now(),
        )
