from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class UserEmployeeContact(BaseModel):
    __tablename__ = "user_employee_contacts"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(String(36), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    user = relationship("User")
    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("user_id", "employee_id"),
    )