"""Identity information only; measurements belong to the metrics API."""

from pydantic import BaseModel, ConfigDict, Field


class ServerInfo(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(ge=1)
    name: str = Field(min_length=1)
    hostname: str = Field(min_length=1)
    os_type: str = Field(min_length=1)
    os_name: str = Field(min_length=1)
    os_version: str = Field(min_length=1)
    architecture: str = Field(min_length=1)
