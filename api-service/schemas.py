# Handles input/output data validation

from pydantic import BaseModel, Field

# Shared fields and validation rules


class Tea(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    origin: str = Field(..., min_length=1, max_length=100)

# Payload schema structure required to CREATE a tea record


class TeaCreate(Tea):
    pass

# Payload schema structure returned back to the CLIENT (includes database IDs)


class TeaResponse(Tea):
    id: int


class config:
    from_attributes = True  # Allows Pydantic to read raw SQLAlchemy database elements
