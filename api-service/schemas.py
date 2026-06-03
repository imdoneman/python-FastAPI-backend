from pydantic import BaseModel, Field

class TeaBase(BaseModel):
    name: str = Field(..., description="The name of the tea", examples=["Matcha Green Tea"])
    origin: str = Field(..., description="The country or region of origin", examples=["Japan"])

class TeaCreate(TeaBase):
    pass

class TeaResponse(TeaBase):
    id: int

class Config:
    # Allows Pydantic to read SQLAlchemy ORM objects seamlessly
    from_attributes = True