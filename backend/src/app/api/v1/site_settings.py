"""
Site Settings API Endpoints

Public endpoints for reading site configuration.
Admin endpoints for updating site configuration.
"""

import os
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.models.site_settings import SiteSettings
from app.schemas.site_settings import (
    SiteSettingsUpdate,
    WebConfigSchema,
    PaymentConfigSchema,
    HomeConfigSchema,
)
from app.schemas.base import SuccessResponse
from app.core.logger import get_logger
from fastapi.responses import FileResponse

router = APIRouter(prefix="/site-settings", tags=["site-settings"])
logger = get_logger(__name__)

# Logo upload directory
LOGO_UPLOAD_DIR = "/app/src/app/data/uploads/logos"
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB


def require_superuser(current_user: dict):
    is_superuser = current_user.get("is_superuser")
    role = current_user.get("role")
    
    if is_superuser:
        return current_user
        
    if role in ["admin", "super_admin"]:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superuser access required"
    )


async def get_or_create_settings(db: AsyncSession) -> SiteSettings:
    """Get site settings or create default if not exists"""
    stmt = select(SiteSettings).where(SiteSettings.id == 1)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()
    
    if not settings:
        # Create default settings
        settings = SiteSettings(
            id=1,
            features_list=[
                {"icon": "Bot", "title": "AI Agents Thông Minh", "description": "Tạo và quản lý nhiều AI agents với khả năng tùy biến cao, hỗ trợ đa ngôn ngữ và tích hợp đa nền tảng."},
                {"icon": "Shield", "title": "Bảo mật & Riêng tư", "description": "Dữ liệu của bạn được mã hóa end-to-end. Tuân thủ các tiêu chuẩn bảo mật quốc tế."},
                {"icon": "TrendingUp", "title": "Mở rộng dễ dàng", "description": "Từ cá nhân đến doanh nghiệp lớn. Nâng cấp gói dịch vụ linh hoạt theo nhu cầu."},
            ],
            testimonials_list=[
                {"id": 1, "name": "Nguyễn Văn A", "role": "CEO, Tech Startup", "content": "Xiaozhi AI đã giúp chúng tôi tự động hóa 70% công việc chăm sóc khách hàng. ROI tăng 300% sau 3 tháng.", "avatar": "https://ui-avatars.com/api/?name=Nguyen+Van+A&background=3b82f6&color=fff", "rating": 5},
                {"id": 2, "name": "Trần Thị B", "role": "Product Manager, E-commerce", "content": "Dễ sử dụng, tích hợp nhanh chóng. AI Agent thông minh hơn tôi tưởng tượng rất nhiều.", "avatar": "https://ui-avatars.com/api/?name=Tran+Thi+B&background=10b981&color=fff", "rating": 5},
                {"id": 3, "name": "Lê Minh C", "role": "Smart Home Enthusiast", "content": "Điều khiển nhà thông minh bằng giọng nói tiếng Việt cực kỳ mượt mà. 10/10!", "avatar": "https://ui-avatars.com/api/?name=Le+Minh+C&background=f59e0b&color=fff", "rating": 5},
            ],
            menu_items=[
                {"label": "Tính năng", "href": "#features", "external": False},
                {"label": "Bảng giá", "href": "#pricing", "external": False},
                {"label": "Đánh giá", "href": "#testimonials", "external": False},
                {"label": "Liên hệ", "href": "#contact", "external": False},
            ],
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


def settings_to_response(settings: SiteSettings) -> dict:
    """Convert SiteSettings model to response dict"""
    return {
        "web": {
            "site_name": settings.site_name,
            "site_description": settings.site_description,
            "site_logo": settings.site_logo,
            "primary_color": settings.primary_color,
            "contact_email": settings.contact_email,
            "support_phone": settings.support_phone,
        },
        "payment": {
            "bank_name": settings.bank_name,
            "bank_code": settings.bank_code,
            "account_number": settings.account_number,
            "account_name": settings.account_name,
            "bank_branch": settings.bank_branch,
            "transfer_content_template": settings.transfer_content_template,
            "enable_qr_code": settings.enable_qr_code,
        },
        "branding": {
            "parent_company_name": getattr(settings, 'parent_company_name', 'Bizino.AI'),
            "parent_company_url": getattr(settings, 'parent_company_url', 'https://bizino.ai'),
            "company_badge_text": getattr(settings, 'company_badge_text', 'by Bizino.AI'),
        },
        "home": {
            "hero": {
                "hero_title": settings.hero_title,
                "hero_subtitle": settings.hero_subtitle,
                "hero_badge_text": settings.hero_badge_text,
                "hero_cta_primary": settings.hero_cta_primary,
                "hero_cta_secondary": settings.hero_cta_secondary,
            },
            "hero_stats": {
                "hero_stats": getattr(settings, 'hero_stats', None) or [],
            },
            "features": {
                "features_enabled": settings.features_enabled,
                "features_title": settings.features_title,
                "features_subtitle": settings.features_subtitle,
                "features_list": settings.features_list or [],
            },
            "solutions": {
                "solutions_enabled": getattr(settings, 'solutions_enabled', True),
                "solutions_title": getattr(settings, 'solutions_title', 'Giải pháp'),
                "solutions_subtitle": getattr(settings, 'solutions_subtitle', ''),
                "solutions_list": getattr(settings, 'solutions_list', None) or [],
            },
            "pricing": {
                "pricing_enabled": settings.pricing_enabled,
                "pricing_title": settings.pricing_title,
                "pricing_subtitle": settings.pricing_subtitle,
            },
            "cta": {
                "cta_enabled": settings.cta_enabled,
                "cta_title": settings.cta_title,
                "cta_subtitle": settings.cta_subtitle,
                "cta_button_text": settings.cta_button_text,
                "cta_button_secondary_text": getattr(settings, 'cta_button_secondary_text', ''),
                "cta_button_secondary_href": getattr(settings, 'cta_button_secondary_href', ''),
            },
            "testimonials": {
                "testimonials_enabled": settings.testimonials_enabled,
                "testimonials_title": settings.testimonials_title,
                "testimonials_subtitle": settings.testimonials_subtitle,
                "testimonials_list": settings.testimonials_list or [],
            },
            "faq": {
                "faq_enabled": getattr(settings, 'faq_enabled', True),
                "faq_title": getattr(settings, 'faq_title', 'Câu hỏi thường gặp'),
                "faq_subtitle": getattr(settings, 'faq_subtitle', ''),
                "faq_list": getattr(settings, 'faq_list', None) or [],
            },
            "footer": {
                "footer_brand_description": settings.footer_brand_description,
                "footer_copyright": settings.footer_copyright,
                "footer_address": settings.footer_address,
                "footer_social_facebook": settings.footer_social_facebook,
                "footer_social_twitter": settings.footer_social_twitter,
                "footer_social_linkedin": settings.footer_social_linkedin,
            },
            "menu": {
                "menu_items": settings.menu_items or [],
            },
        },
    }


# ============== PUBLIC ENDPOINTS ==============

@router.get("", response_model=dict)
async def get_site_settings(
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> Any:
    """
    Get all site settings (public).
    
    Used by frontend to render HomePage and other public pages.
    Returns a minimal fallback response if database errors occur.
    """
    try:
        settings = await get_or_create_settings(db)
        return settings_to_response(settings)
    except Exception as e:
        logger.error(f"Error fetching site settings: {e}")
        # Return a minimal fallback instead of 500 — this prevents the entire
        # frontend from breaking when the site_settings table is missing columns
        return {
            "web": {
                "site_name": "Xiaozhi AI",
                "site_description": "Nền tảng AI Agent thông minh",
                "site_logo": "/logo.png",
                "primary_color": "#3b82f6",
                "contact_email": "",
                "support_phone": "",
            },
            "payment": {
                "bank_name": "", "bank_code": "", "account_number": "",
                "account_name": "", "bank_branch": "",
                "transfer_content_template": "", "enable_qr_code": False,
            },
            "branding": {
                "parent_company_name": "Bizino.AI",
                "parent_company_url": "https://bizino.ai",
                "company_badge_text": "by Bizino.AI",
            },
            "home": {
                "hero": {"hero_title": "", "hero_subtitle": "", "hero_badge_text": "", "hero_cta_primary": "", "hero_cta_secondary": ""},
                "hero_stats": {"hero_stats": []},
                "features": {"features_enabled": True, "features_title": "", "features_subtitle": "", "features_list": []},
                "solutions": {"solutions_enabled": False, "solutions_title": "", "solutions_subtitle": "", "solutions_list": []},
                "pricing": {"pricing_enabled": True, "pricing_title": "", "pricing_subtitle": ""},
                "cta": {"cta_enabled": True, "cta_title": "", "cta_subtitle": "", "cta_button_text": "", "cta_button_secondary_text": "", "cta_button_secondary_href": ""},
                "testimonials": {"testimonials_enabled": False, "testimonials_title": "", "testimonials_subtitle": "", "testimonials_list": []},
                "faq": {"faq_enabled": False, "faq_title": "", "faq_subtitle": "", "faq_list": []},
                "footer": {"footer_brand_description": "", "footer_copyright": "", "footer_address": "", "footer_social_facebook": "", "footer_social_twitter": "", "footer_social_linkedin": ""},
                "menu": {"menu_items": []},
            },
        }


@router.get("/home", response_model=dict)
async def get_home_settings(
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> Any:
    """
    Get only home page settings (public).
    
    Lightweight endpoint for HomePage rendering.
    """
    try:
        settings = await get_or_create_settings(db)
        response = settings_to_response(settings)
        return response["home"]
    except Exception as e:
        logger.error(f"Error fetching home settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch home settings"
        )


# ============== ADMIN ENDPOINTS ==============

@router.put("", response_model=SuccessResponse[dict])
@router.post("/admin", response_model=SuccessResponse[dict])
async def update_site_settings(
    data: SiteSettingsUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """
    Update site settings (admin only).
    
    Partial update - only fields provided will be updated.
    """
    require_superuser(current_user)
    
    try:
        settings = await get_or_create_settings(db)
        
        # Update web config
        if data.web:
            settings.site_name = data.web.site_name
            settings.site_description = data.web.site_description
            settings.site_logo = data.web.site_logo
            settings.primary_color = data.web.primary_color
            settings.contact_email = data.web.contact_email
            settings.support_phone = data.web.support_phone
        
        # Update payment config
        if data.payment:
            settings.bank_name = data.payment.bank_name
            settings.bank_code = data.payment.bank_code
            settings.account_number = data.payment.account_number
            settings.account_name = data.payment.account_name
            settings.bank_branch = data.payment.bank_branch
            settings.transfer_content_template = data.payment.transfer_content_template
            settings.enable_qr_code = data.payment.enable_qr_code
        
        # Update home config
        if data.home:
            # Hero
            if data.home.hero:
                settings.hero_title = data.home.hero.hero_title
                settings.hero_subtitle = data.home.hero.hero_subtitle
                settings.hero_badge_text = data.home.hero.hero_badge_text
                settings.hero_cta_primary = data.home.hero.hero_cta_primary
                settings.hero_cta_secondary = data.home.hero.hero_cta_secondary
            
            # Features
            if data.home.features:
                settings.features_enabled = data.home.features.features_enabled
                settings.features_title = data.home.features.features_title
                settings.features_subtitle = data.home.features.features_subtitle
                settings.features_list = [f.model_dump() for f in data.home.features.features_list]
            
            # Pricing
            if data.home.pricing:
                settings.pricing_enabled = data.home.pricing.pricing_enabled
                settings.pricing_title = data.home.pricing.pricing_title
                settings.pricing_subtitle = data.home.pricing.pricing_subtitle
            
            # CTA
            if data.home.cta:
                settings.cta_enabled = data.home.cta.cta_enabled
                settings.cta_title = data.home.cta.cta_title
                settings.cta_subtitle = data.home.cta.cta_subtitle
                settings.cta_button_text = data.home.cta.cta_button_text
            
            # Testimonials
            if data.home.testimonials:
                settings.testimonials_enabled = data.home.testimonials.testimonials_enabled
                settings.testimonials_title = data.home.testimonials.testimonials_title
                settings.testimonials_subtitle = data.home.testimonials.testimonials_subtitle
                settings.testimonials_list = [t.model_dump() for t in data.home.testimonials.testimonials_list]
            
            # Footer
            if data.home.footer:
                settings.footer_brand_description = data.home.footer.footer_brand_description
                settings.footer_copyright = data.home.footer.footer_copyright
                settings.footer_address = data.home.footer.footer_address
                settings.footer_social_facebook = data.home.footer.footer_social_facebook
                settings.footer_social_twitter = data.home.footer.footer_social_twitter
                settings.footer_social_linkedin = data.home.footer.footer_social_linkedin
            
            # Menu
            if data.home.menu:
                settings.menu_items = [m.model_dump() for m in data.home.menu.menu_items]
        
        await db.commit()
        await db.refresh(settings)
        
        logger.info(f"Site settings updated by admin {current_user.get('id')}")
        
        return SuccessResponse(
            success=True,
            message="Site settings updated successfully",
            data=settings_to_response(settings)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating site settings: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update site settings: {str(e)}"
        )


@router.put("/web", response_model=SuccessResponse[dict])
async def update_web_config(
    data: WebConfigSchema,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """Update web configuration only (admin)"""
    require_superuser(current_user)
    
    settings = await get_or_create_settings(db)
    settings.site_name = data.site_name
    settings.site_description = data.site_description
    settings.site_logo = data.site_logo
    settings.primary_color = data.primary_color
    settings.contact_email = data.contact_email
    settings.support_phone = data.support_phone
    
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Web config updated",
        data=data.model_dump()
    )


@router.put("/payment", response_model=SuccessResponse[dict])
async def update_payment_config(
    data: PaymentConfigSchema,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """Update payment configuration only (admin)"""
    require_superuser(current_user)
    
    settings = await get_or_create_settings(db)
    settings.bank_name = data.bank_name
    settings.bank_code = data.bank_code
    settings.account_number = data.account_number
    settings.account_name = data.account_name
    settings.bank_branch = data.bank_branch
    settings.transfer_content_template = data.transfer_content_template
    settings.enable_qr_code = data.enable_qr_code
    
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Payment config updated",
        data=data.model_dump()
    )


@router.put("/home", response_model=SuccessResponse[dict])
async def update_home_config(
    data: HomeConfigSchema,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """Update home page configuration only (admin)"""
    require_superuser(current_user)
    
    settings = await get_or_create_settings(db)
    
    # Hero
    settings.hero_title = data.hero.hero_title
    settings.hero_subtitle = data.hero.hero_subtitle
    settings.hero_badge_text = data.hero.hero_badge_text
    settings.hero_cta_primary = data.hero.hero_cta_primary
    settings.hero_cta_secondary = data.hero.hero_cta_secondary
    
    # Features
    settings.features_enabled = data.features.features_enabled
    settings.features_title = data.features.features_title
    settings.features_subtitle = data.features.features_subtitle
    settings.features_list = [f.model_dump() for f in data.features.features_list]
    
    # Pricing
    settings.pricing_enabled = data.pricing.pricing_enabled
    settings.pricing_title = data.pricing.pricing_title
    settings.pricing_subtitle = data.pricing.pricing_subtitle
    
    # CTA
    settings.cta_enabled = data.cta.cta_enabled
    settings.cta_title = data.cta.cta_title
    settings.cta_subtitle = data.cta.cta_subtitle
    settings.cta_button_text = data.cta.cta_button_text
    
    # Testimonials
    settings.testimonials_enabled = data.testimonials.testimonials_enabled
    settings.testimonials_title = data.testimonials.testimonials_title
    settings.testimonials_subtitle = data.testimonials.testimonials_subtitle
    settings.testimonials_list = [t.model_dump() for t in data.testimonials.testimonials_list]
    
    # Footer
    settings.footer_brand_description = data.footer.footer_brand_description
    settings.footer_copyright = data.footer.footer_copyright
    settings.footer_address = data.footer.footer_address
    settings.footer_social_facebook = data.footer.footer_social_facebook
    settings.footer_social_twitter = data.footer.footer_social_twitter
    settings.footer_social_linkedin = data.footer.footer_social_linkedin
    
    # Menu
    settings.menu_items = [m.model_dump() for m in data.menu.menu_items]
    
    await db.commit()
    
    return SuccessResponse(
        success=True,
        message="Home config updated",
        data=data.model_dump()
    )


@router.post("/upload-logo", response_model=SuccessResponse[dict])
async def upload_logo(
    file: Annotated[UploadFile, File(description="Logo image file (PNG, JPG, WEBP, SVG)")],
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """
    Upload site logo (admin only).
    
    Accepts PNG, JPG, WEBP, SVG files up to 2MB.
    Returns the URL path to the uploaded logo.
    """
    require_superuser(current_user)
    
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: PNG, JPG, WEBP, SVG"
        )
    
    # Read file content
    content = await file.read()
    
    # Validate file size
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_LOGO_SIZE / (1024 * 1024):.1f}MB"
        )
    
    # Create upload directory if not exists
    os.makedirs(LOGO_UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename or "logo.png")[1] or ".png"
    filename = f"logo_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(LOGO_UPLOAD_DIR, filename)
    
    # Save file
    try:
        with open(filepath, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save logo file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save logo file"
        )
    
    # Update settings with new logo URL
    logo_url = f"/api/v1/site-settings/logo/{filename}"
    
    settings = await get_or_create_settings(db)
    settings.site_logo = logo_url
    await db.commit()
    
    logger.info(f"Logo uploaded by admin {current_user.get('id')}: {filename}")
    
    return SuccessResponse(
        success=True,
        message="Logo uploaded successfully",
        data={"logo_url": logo_url, "filename": filename}
    )


@router.get("/logo/{filename}")
async def get_logo(filename: str):
    """
    Serve uploaded logo file (public).
    """
    
    filepath = os.path.join(LOGO_UPLOAD_DIR, filename)
    
    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo not found"
        )
    
    # Determine content type
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    content_type = content_types.get(ext, "application/octet-stream")
    
    return FileResponse(filepath, media_type=content_type)
