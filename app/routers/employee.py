from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional, Union

from app.database import get_db
from app.i18nMini import get_translation
from app.models.employee import Employee, EmployeeComment, EmployeePost, PostMedia, EmployeePostLimit
from app.models.appointment import Appointment
from app.models.user import User
from app.models.salon import Salon
from app.models.admin import Admin
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse, EmployeeDetailResponse,
    EmployeeCommentCreate, EmployeeCommentResponse, EmployeePostCreate, EmployeePostResponse,
    EmployeeWaitingStatusUpdate, BulkEmployeeWaitingStatusUpdate,
    EmployeeListResponse, EmployeeDetailResponseWrapper, EmployeePostListResponse, SuccessResponse,
    EmployeeAvatarUpdate, EmployeeCommentListResponse  # ← Buni qo'shing
)
from app.auth.dependencies import get_current_user, get_current_admin
from app.auth.jwt_utils import JWTUtils

router = APIRouter(prefix="/employees", tags=["employees"])

# Xodim o'z avatar rasmini URL orqali yangilashi
@router.put("/me/avatar", response_model=SuccessResponse)
async def update_my_avatar(
    payload: EmployeeAvatarUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xodim o'z profil rasmini (avatar_url) URL orqali yangilaydi"""
    try:
        # Faqat xodimlar uchun ruxsat
        if getattr(current_user, "role", None) != "employee":
            raise HTTPException(status_code=403, detail=get_translation(language, "errors.403"))

        # Joriy xodim yozuvini olish
        employee = db.query(Employee).filter(
            and_(
                Employee.id == current_user.id,
                Employee.is_active == True,
                Employee.deleted_at.is_(None)
            )
        ).first()

        if not employee:
            raise HTTPException(status_code=404, detail=get_translation(language, "errors.404"))

        # Schema validatorlari allaqachon formatni tekshiradi
        employee.avatar_url = payload.avatar_url.strip()
        db.commit()
        db.refresh(employee)

        return {
            "success": True,
            "message": get_translation(language, "success"),
            "data": {
                "employee_id": str(employee.id),
                "avatar_url": employee.avatar_url,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Xodim o'z ish vaqtlarini (HH:MM) yangilashi
class EmployeeWorkHoursPayload(EmployeeUpdate):
    pass

@router.put("/me/work-hours", response_model=SuccessResponse)
async def update_my_work_hours(
    payload: EmployeeWorkHoursPayload,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Xodim o'z ish boshlash/ tugash vaqtlarini yangilaydi"""
    try:
        if getattr(current_user, "role", None) != "employee":
            raise HTTPException(status_code=403, detail=get_translation(language, "errors.403"))

        if payload.work_start_time is None and payload.work_end_time is None:
            raise HTTPException(status_code=400, detail="work_start_time yoki work_end_time talab qilinadi")

        employee = db.query(Employee).filter(
            and_(
                Employee.id == current_user.id,
                Employee.is_active == True,
                Employee.deleted_at.is_(None)
            )
        ).first()

        if not employee:
            raise HTTPException(status_code=404, detail=get_translation(language, "errors.404"))

        update_data = payload.dict(exclude_unset=True)
        if "work_start_time" in update_data:
            employee.work_start_time = update_data["work_start_time"]
        if "work_end_time" in update_data:
            employee.work_end_time = update_data["work_end_time"]

        db.commit()
        db.refresh(employee)

        return {
            "success": True,
            "message": get_translation(language, "success"),
            "data": {
                "employee_id": str(employee.id),
                "work_start_time": employee.work_start_time,
                "work_end_time": employee.work_end_time,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    salon_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Get all employees with pagination and search"""
    try:
        # Check if salon exists when salon_id is provided
        if salon_id:
            salon = db.query(Salon).filter(Salon.id == salon_id).first()
            if not salon:
                raise HTTPException(
                    status_code=404,
                    detail=get_translation(language, "errors.404")
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

        # Prepare mapping for done works (yakunlangan appointmentlar soni)
        employee_ids = [str(emp.id) for (emp, _, _) in results]
        done_works_map = {}
        if employee_ids:
            try:
                rows = (
                    db.query(Appointment.employee_id, func.count(Appointment.id).label('done_count'))
                    .filter(Appointment.employee_id.in_(employee_ids), Appointment.status == 'done')
                    .group_by(Appointment.employee_id)
                    .all()
                )
                done_works_map = {str(r[0]): int(r[1] or 0) for r in rows}
            except Exception:
                done_works_map = {}
        
        # Format response
        employees = []
        for employee, comment_count, avg_rating in results:
            employee = add_multilingual_fields(employee)
            employee.comment_count = comment_count or 0
            employee.avg_rating = float(avg_rating) if avg_rating else 0.0
            # Yakunlangan ishlar sonini qo'shamiz
            employee.done_works = done_works_map.get(str(employee.id), 0)
            # Bir salon kontekstida kelganligi uchun salon nomini to'ldiramiz
            try:
                employee.salon_name = salon.salon_name
            except Exception:
                employee.salon_name = None
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
            detail=get_translation(language, "errors.500")
        )

@router.get("/salon/{salon_id}", response_model=EmployeeListResponse)
async def get_employees_by_salon_id(
    salon_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Get employees by salon ID"""
    print(f"Received salon_id: {salon_id}")
    try:
        # Check if salon exists
        salon = db.query(Salon).where(Salon.id == str(salon_id)).first()
        print(f"Salon found: {salon.salon_name }")
        if not salon:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
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
            try:
                employee.salon_name = salon.salon_name
            except Exception:
                employee.salon_name = None
        
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
            detail=get_translation(language, "errors.500")
        )

@router.get("/{employee_id}", response_model=EmployeeDetailResponseWrapper)
async def get_employee_by_id(
    employee_id: str,
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
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
                detail=get_translation(language, "errors.404")
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
            detail=get_translation(language, "errors.500")
        )

@router.post("/", response_model=SuccessResponse)
async def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Create new employee"""
    try:
        # Admin salonini avtomatik aniqlash
        admin_salon_id = str(current_admin.salon_id) if getattr(current_admin, "salon_id", None) else None

        # Agar bodyda salon_id kelgan bo‘lsa, adminning saloniga mosligini tekshiramiz
        # if employee_data.salon_id and str(employee_data.salon_id) != admin_salon_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail=get_translation(language, "errors.403")
        #     )

        # Check if salon exists (adminning salon_id bo‘yicha)
        salon = db.query(Salon).filter(Salon.id == admin_salon_id).first()
        if not salon:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )

        # Only the salon's own admin can create employees
        if current_admin.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=get_translation(language, "errors.403")
            )

        filters = []
        if employee_data.employee_phone:
            filters.append(Employee.phone == employee_data.employee_phone)
        if employee_data.employee_email:
            filters.append(Employee.email == employee_data.employee_email)
        if employee_data.username:
            filters.append(Employee.username == employee_data.username)

        # Avoid calling or_ with empty filters which can raise errors
        existing_employee = 0
        if filters:
            existing_employee = db.query(Employee).filter(or_(*filters)).count()
        
        if existing_employee:
            raise HTTPException(
                status_code=400,
                detail=get_translation(language, "auth.userExists") 
            )
        
        # Hash password
        hashed_password = JWTUtils.hash_password(employee_data.employee_password)
        
        # Create employee
        new_employee = Employee(
            salon_id=admin_salon_id,
            name=employee_data.employee_name,
            phone=employee_data.employee_phone,
            email=employee_data.employee_email,
            role=employee_data.role,
            username=employee_data.username,
            profession=employee_data.profession,
            employee_password=hashed_password,
            is_active=True,
            work_start_time=employee_data.work_start_time,
            work_end_time=employee_data.work_end_time
        )
        
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        return SuccessResponse(
            success=True,
            message=get_translation(language, "auth.userCreated"),
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
        print(f"Error in create_employee: {str(e)}, {e.__traceback__.tb_lineno}")
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )

@router.put("/{employee_id}", response_model=SuccessResponse)
async def update_employee(
    employee_id: str,
    employee_data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Update employee"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
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
                    detail=get_translation(language, "auth.emailExists")
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
                    detail=get_translation(language, "auth.userExists")
                )
        
        # Update fields
        update_data = employee_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(employee, field, value)
        
        db.commit()
        
        return SuccessResponse(
            success=True,
            message=get_translation(language, "auth.userUpdated"),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )

@router.delete("/{employee_id}", response_model=SuccessResponse)
async def delete_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Delete employee (soft delete)"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )
        
        # Soft delete
        employee.deleted_at = func.now()
        db.commit()
        
        return SuccessResponse(
            success=True,
            message=get_translation(language, "auth.userDeleted"),
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )

@router.post("/{employee_id}/comments", response_model=SuccessResponse)
async def add_employee_comment(
    employee_id: str,
    comment_data: EmployeeCommentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Add comment to employee"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
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
            message=get_translation(language, "success"),
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
            detail=get_translation(language, "errors.500")
        )

@router.post("/{employee_id}/posts", response_model=SuccessResponse)
async def add_employee_post(
    employee_id: str,
    post_data: EmployeePostCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Add post for employee"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
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
                detail=get_translation(language, "errors.403")
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
                detail=get_translation(language, "errors.403")
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
            message=get_translation(language, "success"),
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
            detail=get_translation(language, "errors.500")
        )

@router.get("/{employee_id}/posts", response_model=EmployeePostListResponse)
async def get_employee_posts(
    employee_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Get employee posts"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )
        
        offset = (page - 1) * limit
        
        # Get posts (fetch related info per item to avoid eager-load issues)
        posts_query = db.query(EmployeePost).filter(
            and_(EmployeePost.employee_id == employee_id, EmployeePost.is_active == True)
        ).order_by(desc(EmployeePost.created_at))
        
        # Get total count
        total = posts_query.count()
        
        # Get paginated results
        posts = posts_query.offset(offset).limit(limit).all()
        
        # Format response
        formatted_posts = []
        for post in posts:
            try:
                # Fetch employee and salon info per post
                emp = db.query(Employee).options(joinedload(Employee.salon)).filter(Employee.id == post.employee_id).first()
                media_items = db.query(PostMedia).filter(PostMedia.post_id == post.id).all()

                post_dict = {
                    "id": post.id,
                    "employee_id": post.employee_id,
                    "title": post.title,
                    "description": post.description,
                    "is_active": post.is_active,
                    "created_at": post.created_at,
                    "updated_at": post.updated_at,
                    "employee_name": emp.name if emp else None,
                    "employee_surname": emp.surname if emp else None,
                    "employee_profession": emp.profession if emp else None,
                    "salon_id": emp.salon_id if emp else None,
                    "salon_name": emp.salon.salon_name if emp and emp.salon else None,
                    "media_files": [m.file_path for m in media_items]
                }
                formatted_posts.append(EmployeePostResponse(**post_dict))
            except Exception as fe:
                try:
                    print(f"Format error in get_employee_posts: {fe}. PostID: {post.id}")
                except Exception:
                    pass
        
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
        # Log the underlying error for debugging
        try:
            print(f"Error in get_employee_posts: {str(e)}")
            import traceback
            traceback.print_exc()
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )

@router.patch("/bulk/waiting-status", response_model=SuccessResponse)
async def bulk_update_employee_waiting_status(
    status_data: BulkEmployeeWaitingStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Bulk update employees waiting status (xodim yoki salon admin)"""
    try:
        # Xodim yoki salon admin ruxsat
        if getattr(current_user, "role", None) not in ["employee", "admin"]:
            raise HTTPException(
                status_code=403,
                detail=get_translation(language, "errors.403")
            )

        if not status_data.employee_ids:
            raise HTTPException(
                status_code=400,
                detail=get_translation(language, "errors.400")
            )

        # Admin bo'lsa: o'z salonidagi employee_ids ro'yxatini yangilaydi
        if getattr(current_user, "role", None) == "admin":
            if not getattr(current_user, "salon_id", None):
                raise HTTPException(
                    status_code=403,
                    detail=get_translation(language, "errors.403")
                )
            employees = db.query(Employee).filter(
                and_(
                    Employee.id.in_(status_data.employee_ids),
                    Employee.salon_id == current_user.salon_id,
                )
            ).all()

            if not employees:
                raise HTTPException(
                    status_code=404,
                    detail=get_translation(language, "errors.404")
                )

            for emp in employees:
                emp.is_waiting = status_data.is_waiting
            db.commit()

            return SuccessResponse(
                success=True,
                message=get_translation(language, "success"),
                data={
                    "updated_count": len(employees),
                    "employee_ids": [str(emp.id) for emp in employees],
                    "is_waiting": status_data.is_waiting,
                },
            )

        # Xodim bo'lsa: faqat o'z ID sini o'zgartirishi mumkin
        if str(current_user.id) not in [str(eid) for eid in status_data.employee_ids]:
            raise HTTPException(
                status_code=403,
                detail=get_translation(language, "errors.403")
            )

        employee = db.query(Employee).filter(Employee.id == current_user.id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )

        employee.is_waiting = status_data.is_waiting
        db.commit()

        return SuccessResponse(
            success=True,
            message=get_translation(language, "success"),
            data={"updated_count": 1, "employee_id": str(current_user.id), "is_waiting": status_data.is_waiting}
        )
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )

@router.patch("/{employee_id}/waiting-status", response_model=SuccessResponse)
async def update_employee_waiting_status(
    employee_id: str,
    status_data: EmployeeWaitingStatusUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Update employee waiting status (xodim yoki salon admin)"""
    try:
        # Xodim yoki salon admin ruxsat
        if getattr(current_user, "role", None) not in ["employee", "admin"]:
            raise HTTPException(
                status_code=403,
                detail=get_translation(language, "errors.403")
            )

        # Admin bo'lsa: o'z salonidagi xodimni yangilaydi
        if getattr(current_user, "role", None) == "admin":
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            if not emp:
                raise HTTPException(
                    status_code=404,
                    detail=get_translation(language, "errors.404")
                )
            if str(emp.salon_id) != str(getattr(current_user, "salon_id", None)):
                raise HTTPException(
                    status_code=403,
                    detail=get_translation(language, "errors.403")
                )
            emp.is_waiting = status_data.is_waiting
            db.commit()
            return SuccessResponse(
                success=True,
                message=get_translation(language, "success"),
                data={"id": str(employee_id), "is_waiting": status_data.is_waiting}
            )

        # Xodim bo'lsa: faqat o'zini o'zgartira oladi
        if str(current_user.id) != str(employee_id):
            raise HTTPException(
                status_code=403,
                detail=get_translation(language, "errors.403")
            )

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )
        
        employee.is_waiting = status_data.is_waiting
        db.commit()
        
        return SuccessResponse(
            success=True,
            message=get_translation(language, "success"),
            data={"id": str(employee_id), "is_waiting": status_data.is_waiting}
        )
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )


@router.get("/{employee_id}/comments", response_model=EmployeeCommentListResponse)
async def get_employee_comments(
    employee_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    language: Union[str, None] = Header(None, alias="X-User-language"),
):
    """Get employee comments with pagination"""
    try:
        # Check if employee exists
        employee = db.query(Employee).filter(
            and_(
                Employee.id == employee_id,
                Employee.deleted_at.is_(None)
            )
        ).first()
        
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=get_translation(language, "errors.404")
            )
        
        offset = (page - 1) * limit
        
        # Build query with user info
        query = db.query(EmployeeComment).options(
            joinedload(EmployeeComment.user)
        ).filter(
            EmployeeComment.employee_id == employee_id
        ).order_by(desc(EmployeeComment.created_at))
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        comments = query.offset(offset).limit(limit).all()
        
        # Format response
        formatted_comments = []
        for comment in comments:
            comment_dict = {
                "id": str(comment.id),
                "employee_id": str(comment.employee_id),
                "user_id": str(comment.user_id),
                "text": comment.text,
                "rating": comment.rating,
                "created_at": comment.created_at,
                "full_name": comment.user.full_name if comment.user else None,
                "user_avatar": getattr(comment.user, 'avatar_url', None) if comment.user else None
            }
            formatted_comments.append(EmployeeCommentResponse(**comment_dict))
        
        # Calculate average rating
        avg_rating = 0.0
        if formatted_comments:
            total_rating = sum(c.rating for c in formatted_comments)
            avg_rating = round(total_rating / len(formatted_comments), 1)
        
        return EmployeeCommentListResponse(
            success=True,
            data=formatted_comments,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            },
            avg_rating=avg_rating
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_employee_comments: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=get_translation(language, "errors.500")
        )
