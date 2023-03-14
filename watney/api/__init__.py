from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from typing import List


class BrokenLink(BaseModel):
    file: str
    url: str
    status_code: int


class BrokenLinkRepo(BaseModel):
    repo_name: str
    repo_url: str
    broken_links: List[BrokenLink]


class BrokenLinkReport(BaseModel):
    report: List[BrokenLinkRepo]
    report_date: datetime


class BrokenLinksResponse(BaseModel):
    new_broken_links: List[BrokenLink]
    existing_broken_links: List[BrokenLink]
    last_report_id: UUID
    last_report_date: datetime


