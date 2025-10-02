from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.employee import Employee, EmployeeComment, EmployeePost, PostMedia, EmployeePostLimit
from app.models.user import User
from app.models.salon import Salon
from app.models.admin import Admin
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeDetailResponse,
    EmployeeCommentCreate, EmployeeCommentResponse, EmployeePostCreate, EmployeePostResponse,
    EmployeeWaitingStatusUpdate, BulkEmployeeWaitingStatusUpdate,
    EmployeeListResponse, EmployeeDetailResponseWrapper, EmployeePostListResponse, SuccessResponse
)
from app.auth.dependencies import get_current_user, get_current_admin
from app.auth.jwt_utils import JWTUtils

router = APIRouter(prefix="/employees", tags=["employees"])

def add_multilingual_fields(employee):
    """Add multilingual fields to employee object"""
    # For now, we'll use the same value for all languages
    # In production, you would integrate with translation service
    employee.name_uz = employee.name or ''
    employee.name_en = employee.name or ''
    employee.name_ru = employee.name or ''
    
    employee.surname_uz = employee.surname or ''
    employee.surname_en = employee.surname or ''
    employee.surname_ru = employee.surname or ''
    
    employee.profession_uz = employee.profession or ''
    employee.profession_en = employee.profession or ''
    employee.profession_ru = employee.profession or ''
    
    employee.bio_uz = employee.bio or ''
    employee.bio_en = employee.bio or ''
    employee.bio_ru = employee.bio or ''
    
    employee.specialization_uz = employee.specialization or ''
    employee.specialization_en = employee.specialization or ''
    employee.specialization_ru = employee.specialization or ''
    
    return employee

@router.get("/", response_model=EmployeeListResponse)
async def get_all_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    salon_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all employees with pagination and search"""
    try:
        # Check if salon exists when salon_id is provided
        if salon_id:
            salon = db.query(Salon).filter(Salon.id == salon_id).first()
            if not salon:
                raise HTTPException(
                    status_code=404,
                    detail="Salon topilmadi"
                )
        
        offset = (page - 1) * limit
        
        # Build query
        query = db.query(
            Employee,
            func.count(EmployeeComment.id).label('comment_count'),
            func.avg(EmployeeComment.rating).label('avg_rating')
        ).outerjoin(EmployeeComment).filter(Employee.deleted_at.is_(None))
        
        # Add search filter
        if search:
            search_filter = or_(
                Employee.name.ilike(f"%{search}%"),
                Employee.surname.ilike(f"%{search}%"),
                Employee.profession.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Add salon filter
        if salon_id:
            query = query.filter(Employee.salon_id == salon_id)
        
        # Group by employee and order
        query = query.group_by(Employee.id).order_by(desc(Employee.created_at))
        
        # Get total count
        total_query = db.query(func.count(Employee.id)).filter(Employee.deleted_at.is_(None))
        if search:
            total_query = total_query.filter(search_filter)
        if salon_id:
            total_query = total_query.filter(Employee.salon_id == salon_id)
        total = total_query.scalar()
        
        # Get paginated results
        results = query.offset(offset).limit(limit).all()
        
        # Format response
        employees = []
        for employee, comment_count, avg_rating in results:
            employee = add_multilingual_fields(employee)
            employee.comment_count = comment_count or 0
            employee.avg_rating = float(avg_rating) if avg_rating else 0.0
            employees.append(employee)
        
        return EmployeeListResponse(
            success=True,
            data=employees,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_all_employees: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Xodim ma'lumotlarini olishda xatolik yuz berdi: {str(e)}"
        )

@router.get("/salon/{salon_id}", response_model=EmployeeListResponse)
async def get_employees_by_salon_id(
    salon_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get employees by salon ID"""
    try:
        # Check if salon exists
        salon = db.query(Salon).filter(Salon.id == salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=404,
                detail="Salon topilmadi"
            )
        
        offset = (page - 1) * limit
        
        # Build query
        query = db.query(
            Employee,
            func.count(EmployeeComment.id).label('comment_count'),
            func.avg(EmployeeComment.rating).label('avg_rating')
        ).outerjoin(EmployeeComment).filter(
            and_(Employee.salon_id == salon_id, Employee.deleted_at.is_(None))
        )
        
        # Add search filter
        if search:
            search_filter = or_(
                Employee.name.ilike(f"%{search}%"),
                Employee.surname.ilike(f"%{search}%"),
                Employee.profession.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Group by employee and order
        query = query.group_by(Employee.id).order_by(desc(Employee.created_at))
        
        # Get total count
        total_query = db.query(func.count(Employee.id)).filter(
            and_(Employee.salon_id == salon_id, Employee.deleted_at.is_(None))
        )
        if search:
            total_query = total_query.filter(search_filter)
        total = total_query.scalar()
        
        # Get paginated results
        results = query.offset(offset).limit(limit).all()
        
        # Format response with translations
        employees = []
        for employee, comment_count, avg_rating in results:
            employee = add_multilingual_fields(employee)
            employee.comment_count = comment_count or 0
            employee.avg_rating = float(avg_rating) if avg_rating else 0.0
            employees.append(employee)
        
        return EmployeeListResponse(
            success=True,
            data=employees,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Xodimlarni olishda xatolik yuz berdi"
        )

@router.get("/{employee_id}", response_model=EmployeeDetailResponseWrapper)
async def get_employee_by_id(
    employee_id: UUID,
    db: Session = Depends(get_db)
):
    """Get employee by ID with comments and posts"""
    try:
        # Get employee with salon info
        employee = db.query(Employee).options(
            joinedload(Employee.salon)
        ).filter(
            and_(Employee.id == employee_id, Employee.deleted_at.is_(None))
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Xodim topilmadi"
            )
        
        # Add multilingual fields
        employee = add_multilingual_fields(employee)
        employee.salon_name = employee.salon.salon_name if employee.salon else None
        
        # Get comments with user info (temporarily disabled)
        comments = []
        
        # Get posts (temporarily disabled due to missing post_media table)
        posts = []
        
        # Format comments
        formatted_comments = []
        for comment in comments:
            comment_dict = {
                "id": comment.id,
                "employee_id": comment.employee_id,
                "user_id": comment.user_id,
                "text": comment.text,
                "rating": comment.rating,
                "created_at": comment.created_at,
                "full_name": comment.user.full_name if comment.user else None
            }
            formatted_comments.append(comment_dict)
        
        # Format posts
        formatted_posts = []
        for post in posts:
            post_dict = {
                "id": post.id,
                "employee_id": post.employee_id,
                "title": post.title,
                "description": post.description,
                "is_active": post.is_active,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "media": [media.file_path for media in post.media] if post.media else []
            }
            formatted_posts.append(post_dict)
        
        # Calculate average rating
        avg_rating = 0.0
        if formatted_comments:
            total_rating = sum(comment["rating"] for comment in formatted_comments)
            avg_rating = round(total_rating / len(formatted_comments), 1)
        
        # Create response
        employee_dict = employee.__dict__.copy()
        employee_dict.pop('rating', None)  # Remove existing rating to avoid conflict
        employee_data = EmployeeDetailResponse(
            **employee_dict,
            rating=avg_rating,
            comments=formatted_comments,
            posts=formatted_posts
        )
        
        return EmployeeDetailResponseWrapper(
            success=True,
            data=employee_data
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_employee_by_id: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Xodim ma'lumotlarini olishda xatolik yuz berdi: {str(e)}"
        )

@router.post("/", response_model=SuccessResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Create new employee"""
    try:
        # Check if salon exists
        salon = db.query(Salon).filter(Salon.id == employee_data.salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=404,
                detail="Salon topilmadi"
            )
        
        # Check if phone, email or username already exists
        existing_employee = db.query(Employee).filter(
            or_(
                Employee.phone == employee_data.employee_phone,
                Employee.email == employee_data.employee_email,
                Employee.username == employee_data.username
            )
        ).first()
        
        if existing_employee:
            raise HTTPException(
                status_code=400,
                detail="Telefon raqam, email yoki username allaqachon mavjud"
            )
        
        # Hash password
        hashed_password = JWTUtils.hash_password(employee_data.employee_password)
        
        # Create employee
        new_employee = Employee(
            salon_id=employee_data.salon_id,
            name=employee_data.employee_name,
            phone=employee_data.employee_phone,
            email=employee_data.employee_email,
            role=employee_data.role,
            username=employee_data.username,
            profession=employee_data.profession,
            employee_password=hashed_password,
            is_active=True
        )
        
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        return SuccessResponse(
            success=True,
            message="Xodim muvaffaqiyatli yaratildi",
            data={
                "id": str(new_employee.id),
                "salon_id": str(new_employee.salon_id),
                "name": new_employee.name,
                "phone": new_employee.phone,
                "email": new_employee.email,
                "role": new_employee.role,
                "username": new_employee.username,
                "profession": new_employee.profession
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in create_employee: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Xodim yaratishda xatolik yuz berdi"
        )

@router.put("/{employee_id}", response_model=SuccessResponse)
async def update_employee(
    employee_id: UUID,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Update employee"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Xodim topilmadi"
            )
        
        # Check if email already exists for other employees
        if employee_data.email:
            duplicate = db.query(Employee).filter(
                and_(
                    Employee.email == employee_data.email,
                    Employee.id != employee_id
                )
            ).first()
            
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail="Email allaqachon mavjud"
                )
        
        # Check if username already exists for other employees
        if employee_data.username:
            duplicate = db.query(Employee).filter(
                and_(
                    Employee.username == employee_data.username,
                    Employee.id != employee_id
                )
            ).first()
            
            if duplicate:
                raise HTTPException(
                    status_code=400,
                    detail="Username allaqachon mavjud"
                )
        
        # Update fields
        update_data = employee_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(employee, field, value)
        
        db.commit()
        
        return SuccessResponse(
            success=True,
            message="Xodim ma'lumotlari muvaffaqiyatli yangilandi"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Xodim ma'lumotlarini yangilashda xatolik yuz berdi"
        )

@router.delete("/{employee_id}", response_model=SuccessResponse)
async def delete_employee(
    employee_id: UUID,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Delete employee (soft delete)"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Xodim topilmadi"
            )
        
        # Soft delete
        employee.deleted_at = func.now()
        db.commit()
        
        return SuccessResponse(
            success=True,
            message="Xodim muvaffaqiyatli o'chirildi"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Xodimni o'chirishda xatolik yuz berdi"
        )

@router.post("/{employee_id}/comments", response_model=SuccessResponse)
async def add_employee_comment(
    employee_id: UUID,
    comment_data: EmployeeCommentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add comment to employee"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Xodim topilmadi"
            )
        
        # Create comment
        new_comment = EmployeeComment(
            employee_id=employee_id,
            user_id=current_user.id,
            text=comment_data.text,
            rating=comment_data.rating
        )
        
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return SuccessResponse(
            success=True,
            message="Izoh muvaffaqiyatli qo'shildi",
            data={
                "id": str(new_comment.id),
                "employee_id": str(employee_id),
                "user_id": str(current_user.id),
                "text": comment_data.text,
                "rating": comment_data.rating
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Izoh qo'shishda xatolik yuz berdi"
        )

@router.post("/{employee_id}/posts", response_model=SuccessResponse)
async def add_employee_post(
    employee_id: UUID,
    post_data: EmployeePostCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add post for employee"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Xodim topilmadi"
            )
        
        # Auto-create admin record if it doesn't exist for this employee
        admin_record = db.query(Admin).filter(Admin.id == employee_id).first()
        if not admin_record:
            # Create admin record for employee
            from app.auth.jwt_utils import JWTUtils
            
            # Use employee's existing password or create a default one
            default_password = "12345678"  # Default password for auto-created admin records
            hashed_password = JWTUtils.hash_password(default_password)
            
            admin_record = Admin(
                id=employee_id,  # Use employee ID as admin ID
                username=employee.name.lower().replace(" ", "_"),  # Create username from name
                email=f"{employee.name.lower().replace(' ', '_')}@example.com",  # Default email
                password_hash=hashed_password,
                full_name=employee.name,
                phone=employee.phone,
                is_active=True,
                role="admin",  # Set role as admin for proper access
                salon_id=employee.salon_id
            )
            
            db.add(admin_record)
            db.commit()
            db.refresh(admin_record)
        
        # Check if current user is the employee or admin/superadmin
        if str(employee.id) != str(current_user.id) and current_user.role not in ["admin", "superadmin"]:
            raise HTTPException(
                status_code=403,
                detail="Siz faqat o'zingizning postlaringizni qo'sha olasiz"
            )
        
        # Get or create post limits
        limits = db.query(EmployeePostLimit).filter(
            EmployeePostLimit.employee_id == employee_id
        ).first()
        
        if not limits:
            limits = EmployeePostLimit(employee_id=employee_id)
            db.add(limits)
            db.commit()
            db.refresh(limits)
        
        # Check limits
        remaining_free_posts = max(0, 4 - limits.free_posts_used)
        used_paid_posts = max(0, limits.free_posts_used - 4)
        remaining_paid_posts = max(0, limits.total_paid_posts - used_paid_posts)
        
        if remaining_free_posts == 0 and remaining_paid_posts == 0:
            raise HTTPException(
                status_code=403,
                detail="Post limiti tugagan. Yangi postlar uchun to'lov qiling."
            )
        
        # Create post
        new_post = EmployeePost(
            employee_id=employee_id,
            title=post_data.title,
            description=post_data.description
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        # Add media files
        if post_data.media:
            for file_path in post_data.media:
                media = PostMedia(
                    post_id=new_post.id,
                    file_path=file_path
                )
                db.add(media)
        
        # Update limits
        limits.free_posts_used += 1
        db.commit()
        
        # Calculate new limits
        new_remaining_free = max(0, 4 - limits.free_posts_used)
        new_used_paid = max(0, limits.free_posts_used - 4)
        new_remaining_paid = max(0, limits.total_paid_posts - new_used_paid)
        
        return SuccessResponse(
            success=True,
            message="Post muvaffaqiyatli qo'shildi",
            data={
                "id": str(new_post.id),
                "employee_id": str(employee_id),
                "title": post_data.title,
                "description": post_data.description,
                "media": post_data.media,
                "limits": {
                    "free_posts_used": limits.free_posts_used,
                    "total_paid_posts": limits.total_paid_posts,
                    "remaining_free_posts": new_remaining_free,
                    "remaining_paid_posts": new_remaining_paid
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Post qo'shishda xatolik yuz berdi"
        )

@router.get("/{employee_id}/posts", response_model=EmployeePostListResponse)
async def get_employee_posts(
    employee_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get employee posts"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Employee topilmadi"
            )
        
        offset = (page - 1) * limit
        
        # Get posts with employee and salon info
        posts_query = db.query(EmployeePost).options(
            joinedload(EmployeePost.employee).joinedload(Employee.salon),
            joinedload(EmployeePost.media)
        ).filter(
            and_(EmployeePost.employee_id == employee_id, EmployeePost.is_active == True)
        ).order_by(desc(EmployeePost.created_at))
        
        # Get total count
        total = posts_query.count()
        
        # Get paginated results
        posts = posts_query.offset(offset).limit(limit).all()
        
        # Format response
        formatted_posts = []
        for post in posts:
            post_dict = {
                "id": post.id,
                "employee_id": post.employee_id,
                "title": post.title,
                "description": post.description,
                "is_active": post.is_active,
                "created_at": post.created_at,
                "updated_at": post.updated_at,
                "employee_name": post.employee.name if post.employee else None,
                "employee_surname": post.employee.surname if post.employee else None,
                "employee_profession": post.employee.profession if post.employee else None,
                "salon_id": post.employee.salon_id if post.employee else None,
                "salon_name": post.employee.salon.name if post.employee and post.employee.salon else None,
                "media_files": [media.file_path for media in post.media] if post.media else []
            }
            formatted_posts.append(EmployeePostResponse(**post_dict))
        
        return EmployeePostListResponse(
            success=True,
            data=formatted_posts,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Server xatosi yuz berdi"
        )

@router.patch("/bulk/waiting-status", response_model=SuccessResponse)
async def bulk_update_employee_waiting_status(
    status_data: BulkEmployeeWaitingStatusUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Bulk update employees waiting status"""
    try:
        if not status_data.employee_ids:
            raise HTTPException(
                status_code=400,
                detail="employee_ids array bo'lishi va bo'sh bo'lmasligi kerak"
            )
        
        # Update employees
        updated_count = db.query(Employee).filter(
            Employee.id.in_(status_data.employee_ids)
        ).update(
            {"is_waiting": status_data.is_waiting},
            synchronize_session=False
        )
        
        db.commit()
        
        return SuccessResponse(
            success=True,
            message=f"{updated_count} ta xodim holati muvaffaqiyatli yangilandi",
            data={
                "updated_count": updated_count,
                "employee_ids": [str(id) for id in status_data.employee_ids],
                "is_waiting": status_data.is_waiting
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Server xatosi"
        )

@router.patch("/{employee_id}/waiting-status", response_model=SuccessResponse)
async def update_employee_waiting_status(
    employee_id: UUID,
    status_data: EmployeeWaitingStatusUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Update employee waiting status"""
    try:
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail="Xodim topilmadi"
            )
        
        employee.is_waiting = status_data.is_waiting
        db.commit()
        
        return SuccessResponse(
            success=True,
            message="Xodim holati muvaffaqiyatli yangilandi",
            data={"id": str(employee_id), "is_waiting": status_data.is_waiting}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Server xatosi"
        )