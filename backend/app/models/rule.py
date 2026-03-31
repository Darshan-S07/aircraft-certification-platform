from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_number = Column(String, nullable=False)
    type = Column(String, nullable=False)  # CS / AMC / GM
    title = Column(String)
    text = Column(Text)

    # 🔥 NEW
    references = Column(Text)   # store JSON list

    subpart = Column(String, nullable=True)

    regulation_id = Column(Integer, ForeignKey("regulations.id"))
    regulation = relationship("Regulation", back_populates="rules")

    __table_args__ = (
        UniqueConstraint("rule_number", "type", "regulation_id", name="unique_rule"),
    )