
from pydantic import BaseModel, ConfigDict, Field


class Tea(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    origin: str = Field(..., min_length=1, max_length=100)


class TeaCreate(Tea):
    pass


class TeaResponse(Tea):
    id: int

    model_config = ConfigDict(from_attributes=True)
