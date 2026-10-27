from pydantic import BaseModel, ConfigDict, Field


class TeaBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The name of the tea",
        examples=["Matcha Green Tea"],
    )
    origin: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="The country or region of origin",
        examples=["Japan"],
    )


class TeaCreate(TeaBase):
    pass


class TeaResponse(TeaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int