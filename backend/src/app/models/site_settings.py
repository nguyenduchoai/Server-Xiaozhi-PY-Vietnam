"""
Site Settings Model

Stores configurable settings for the website including:
- Web config (site name, logo, colors, contact info)
- Payment config (bank info, QR settings)
- Home page config (hero, sections, footer)
- Testimonials
"""

from sqlalchemy import String, Text, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.database import Base


class SiteSettings(Base):
    """
    Single-row table storing all site configuration as JSON.
    """
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    
    # Web Config
    site_name: Mapped[str] = mapped_column(String(100), default="Xiaozhi AI")
    site_description: Mapped[str] = mapped_column(Text, default="Nền tảng AI Agent thông minh cho doanh nghiệp")
    site_logo: Mapped[str] = mapped_column(String(255), default="/logo.png")
    primary_color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    contact_email: Mapped[str] = mapped_column(String(100), default="contact@xiaozhi-ai-iot.vn")
    support_phone: Mapped[str] = mapped_column(String(20), default="1900-xxxx")
    
    # Payment Config
    bank_name: Mapped[str] = mapped_column(String(100), default="Vietcombank")
    bank_code: Mapped[str] = mapped_column(String(20), default="VCB")
    account_number: Mapped[str] = mapped_column(String(50), default="0011004295499")
    account_name: Mapped[str] = mapped_column(String(100), default="NGUYEN VAN A")
    bank_branch: Mapped[str] = mapped_column(String(100), default="Chi nhánh Hà Nội")
    transfer_content_template: Mapped[str] = mapped_column(String(255), default="Thanh toan goi {plan_name} - {user_email}")
    enable_qr_code: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Home Page - Hero Section
    hero_title: Mapped[str] = mapped_column(Text, default="Xây dựng AI Agents Thông minh & Mạnh mẽ")
    hero_subtitle: Mapped[str] = mapped_column(Text, default="Quản lý IoT, tự động hóa nhà thông minh, và bán các AI Agent của bạn. Tất cả trong một nền tảng đơn giản.")
    hero_badge_text: Mapped[str] = mapped_column(String(100), default="Nền tảng AI Agent thông minh")
    hero_cta_primary: Mapped[str] = mapped_column(String(50), default="Bắt đầu miễn phí")
    hero_cta_secondary: Mapped[str] = mapped_column(String(50), default="Đăng nhập")
    
    # Home Page - Features Section
    features_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    features_title: Mapped[str] = mapped_column(String(100), default="Tại sao chọn chúng tôi?")
    features_subtitle: Mapped[str] = mapped_column(String(255), default="Nền tảng toàn diện cho mọi nhu cầu AI Agent của bạn")
    features_list: Mapped[dict] = mapped_column(JSON, default=list)  # List of {icon, title, description}
    
    # Home Page - Pricing Section
    pricing_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    pricing_title: Mapped[str] = mapped_column(String(100), default="Bảng giá linh hoạt")
    pricing_subtitle: Mapped[str] = mapped_column(String(255), default="Chọn gói phù hợp với nhu cầu của bạn")
    
    # Home Page - CTA Section
    cta_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cta_title: Mapped[str] = mapped_column(String(100), default="Sẵn sàng bắt đầu?")
    cta_subtitle: Mapped[str] = mapped_column(String(255), default="Tham gia cùng hàng nghìn người dùng đang sử dụng nền tảng AI Agent của chúng tôi")
    cta_button_text: Mapped[str] = mapped_column(String(50), default="Đăng ký miễn phí ngay")
    
    # Home Page - Testimonials Section
    testimonials_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    testimonials_title: Mapped[str] = mapped_column(String(100), default="Khách hàng nói gì?")
    testimonials_subtitle: Mapped[str] = mapped_column(String(255), default="Hàng nghìn người dùng đã tin tưởng sử dụng dịch vụ của chúng tôi")
    testimonials_list: Mapped[dict] = mapped_column(JSON, default=list)  # List of {name, role, content, avatar, rating}
    
    # Footer
    footer_brand_description: Mapped[str] = mapped_column(Text, default="Nền tảng AI Agent thông minh hàng đầu Việt Nam. Tự động hóa mọi thứ với AI.")
    footer_copyright: Mapped[str] = mapped_column(String(255), default="© 2025 Xiaozhi AI. All rights reserved.")
    footer_address: Mapped[str] = mapped_column(String(255), default="Hà Nội, Việt Nam")
    footer_social_facebook: Mapped[str] = mapped_column(String(255), default="")
    footer_social_twitter: Mapped[str] = mapped_column(String(255), default="")
    footer_social_linkedin: Mapped[str] = mapped_column(String(255), default="")
    
    # Menu items (JSON array)
    menu_items: Mapped[dict] = mapped_column(JSON, default=list)  # List of {label, href, external}
    
    # ==========================================
    # NEW: Branding / Parent Company Info
    # ==========================================
    parent_company_name: Mapped[str] = mapped_column(String(100), default="Bizino.AI")
    parent_company_url: Mapped[str] = mapped_column(String(255), default="https://bizino.ai")
    company_badge_text: Mapped[str] = mapped_column(String(100), default="by Bizino.AI")
    
    # ==========================================
    # NEW: Solutions Section (for B2B landing pages)
    # ==========================================
    solutions_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    solutions_title: Mapped[str] = mapped_column(String(100), default="Giải pháp")
    solutions_subtitle: Mapped[str] = mapped_column(String(255), default="Các giải pháp AI của chúng tôi")
    solutions_list: Mapped[dict] = mapped_column(JSON, default=list)  # List of {id, icon, title, subtitle, description, features[], useCases[], gradient, stats{}}
    
    # ==========================================
    # NEW: FAQ Section
    # ==========================================
    faq_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    faq_title: Mapped[str] = mapped_column(String(100), default="Câu hỏi thường gặp")
    faq_subtitle: Mapped[str] = mapped_column(String(255), default="")
    faq_list: Mapped[dict] = mapped_column(JSON, default=list)  # List of {question, answer}
    
    # ==========================================
    # NEW: Hero Stats (displayed in hero section)
    # ==========================================
    hero_stats: Mapped[dict] = mapped_column(JSON, default=list)  # List of {value, label}
    
    # ==========================================
    # NEW: CTA Secondary Button
    # ==========================================
    cta_button_secondary_text: Mapped[str] = mapped_column(String(50), default="")
    cta_button_secondary_href: Mapped[str] = mapped_column(String(255), default="")

    # ==========================================
    # PAY2S PAYMENT GATEWAY CONFIG
    # ==========================================
    pay2s_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    pay2s_sandbox_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    pay2s_partner_code: Mapped[str] = mapped_column(String(50), default="")
    pay2s_access_key: Mapped[str] = mapped_column(String(100), default="")
    pay2s_secret_key: Mapped[str] = mapped_column(Text, default="")
    pay2s_payment_timeout_minutes: Mapped[int] = mapped_column(Integer, default=15)
    pay2s_bank_account_number: Mapped[str] = mapped_column(String(50), default="")
    pay2s_bank_id: Mapped[str] = mapped_column(String(20), default="")  # ACB, VCB, etc.


