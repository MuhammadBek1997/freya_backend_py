from sqlalchemy import Column, String, Boolean, Text, Integer, DECIMAL, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel
from .salon import Salon

class Employee(BaseModel):
    __tablename__ = "employees"

    salon_id = Column(UUID(as_uuid=True), ForeignKey("salons.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    surname = Column(String(100))
    position = Column(String(100))
    phone = Column(String(20), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(100))
    profession = Column(String(100))
    username = Column(String(50), unique=True)
    employee_password = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    bio = Column(Text)
    specialization = Column(String(255))
    experience_years = Column(Integer, default=0)
    rating = Column(DECIMAL(3,2), default=0)
    is_active = Column(Boolean, default=True)
    is_waiting = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    
    # Relationships
    salon = relationship("Salon", back_populates="employees")
    comments = relationship("EmployeeComment", back_populates="employee", cascade="all, delete-orphan")
    posts = relationship("EmployeePost", back_populates="employee", cascade="all, delete-orphan")
    general_posts = relationship("Post", back_populates="employee", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="employee")
    appointments = relationship("Appointment", back_populates="employee")
    user_chats = relationship("UserChat", back_populates="employee")
    translations = relationship("EmployeeTranslation", back_populates="employee", cascade="all, delete-orphan")

class EmployeeComment(BaseModel):
    __tablename__ = "employee_comments"
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    
    # Relationships
    employee = relationship("Employee", back_populates="comments")
    user = relationship("User")

class EmployeePost(BaseModel):
    __tablename__ = "employee_posts"
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    employee = relationship("Employee", back_populates="posts")
    media = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan")

class PostMedia(BaseModel):
    __tablename__ = "post_media"
    
    post_id = Column(UUID(as_uuid=True), ForeignKey("employee_posts.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # Relationships
    post = relationship("EmployeePost", back_populates="media")

class EmployeePostLimit(BaseModel):
    __tablename__ = "employee_post_limits"
    
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    free_posts_used = Column(Integer, default=0)
    total_paid_posts = Column(Integer, default=0)
    
    # Relationships
    employee = relationship("Employee", back_populates="post_limits")

# Employee model'iga post_limits relationship qo'shish
Employee.post_limits = relationship("EmployeePostLimit", back_populates="employee", uselist=False)