from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    version = Column(String, nullable=False)

    rules = relationship("Rule", back_populates="regulation", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint("name", "version", name="unique_regulation"),
    )