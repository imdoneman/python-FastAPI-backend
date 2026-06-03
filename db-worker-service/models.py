from sqlalchemy import Column, Integer, String
from database import Base

class TeaItem(Base):
    __tablename__ = "teas"

    id = Column(Integer, primary_key=True, index=True)
    # The unique constraint ensures we don't insert duplicate teas during RabbitMQ processing
    name = Column(String, unique=True, index=True, nullable=False)
    origin = Column(String, nullable=False)