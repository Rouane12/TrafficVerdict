from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    domain: str = Field(min_length=1, max_length=255)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    domain: str
    timezone: str
