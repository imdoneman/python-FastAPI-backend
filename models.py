# Defines database table structures
from sqlalchemy import Column, Integer, String
from database import Base


class TeaItem(Base):
    __tablename__ = "tea_inventory"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    origin = Column(String, nullable=False)
