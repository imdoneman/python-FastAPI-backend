from sqlalchemy import Column, Integer, String

from database import Base


class TeaItem(Base):
    __tablename__ = "teas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False)
    origin = Column(String(200), nullable=False)