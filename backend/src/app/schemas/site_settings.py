"""
Site Settings Schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class FeatureItem(BaseModel):
    """Single feature item for the features section"""
    icon: str = Field(default="Bot", description="Lucide icon name")
    title: str = Field(default="Feature Title")
    description: str = Field(default="Feature description")


class TestimonialItem(BaseModel):
    """Single testimonial item"""
    id: int = Field(default=1)
    name: str = Field(default="Customer Name")
    role: str = Field(default="CEO, Company")
    content: str = Field(default="Great product!")
    avatar: str = Field(default="")
    rating: int = Field(default=5, ge=1, le=5)


class MenuItem(BaseModel):
    """Navigation menu item"""
    label: str = Field(default="Menu Item")
    href: str = Field(default="#")
    external: bool = Field(default=False)


class SolutionItem(BaseModel):
    """Single solution item for B2B landing pages"""
    id: str = Field(default="solution-1")
    icon: str = Field(default="Bot", description="Lucide icon name")
    title: str = Field(default="Solution Title")
    subtitle: str = Field(default="Solution subtitle")
    description: str = Field(default="Solution description")
    features: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    gradient: str = Field(default="from-blue-600 to-cyan-500")
    stats_value: str = Field(default="")
    stats_label: str = Field(default="")


class FAQItem(BaseModel):
    """Single FAQ item"""
    question: str = Field(default="Question?")
    answer: str = Field(default="Answer.")


class HeroStat(BaseModel):
    """Hero section statistic"""
    value: str = Field(default="100+")
    label: str = Field(default="Users")


class WebConfigSchema(BaseModel):
    """Web configuration settings"""
    site_name: str = Field(default="Xiaozhi AI")
    site_description: str = Field(default="Nền tảng AI Agent thông minh cho doanh nghiệp")
    site_logo: str = Field(default="/logo.png")
    primary_color: str = Field(default="#3b82f6")
    contact_email: str = Field(default="contact@xiaozhi-ai-iot.vn")
    support_phone: str = Field(default="1900-xxxx")


class PaymentConfigSchema(BaseModel):
    """Payment configuration settings"""
    bank_name: str = Field(default="Vietcombank")
    bank_code: str = Field(default="VCB")
    account_number: str = Field(default="0011004295499")
    account_name: str = Field(default="NGUYEN VAN A")
    bank_branch: str = Field(default="Chi nhánh Hà Nội")
    transfer_content_template: str = Field(default="Thanh toan goi {plan_name} - {user_email}")
    enable_qr_code: bool = Field(default=True)


class HeroConfigSchema(BaseModel):
    """Hero section configuration"""
    hero_title: str = Field(default="Xây dựng AI Agents Thông minh & Mạnh mẽ")
    hero_subtitle: str = Field(default="Quản lý IoT, tự động hóa nhà thông minh")
    hero_badge_text: str = Field(default="Nền tảng AI Agent thông minh")
    hero_cta_primary: str = Field(default="Bắt đầu miễn phí")
    hero_cta_secondary: str = Field(default="Đăng nhập")


class FeaturesConfigSchema(BaseModel):
    """Features section configuration"""
    features_enabled: bool = Field(default=True)
    features_title: str = Field(default="Tại sao chọn chúng tôi?")
    features_subtitle: str = Field(default="Nền tảng toàn diện cho mọi nhu cầu AI Agent của bạn")
    features_list: list[FeatureItem] = Field(default_factory=list)


class PricingConfigSchema(BaseModel):
    """Pricing section configuration"""
    pricing_enabled: bool = Field(default=True)
    pricing_title: str = Field(default="Bảng giá linh hoạt")
    pricing_subtitle: str = Field(default="Chọn gói phù hợp với nhu cầu của bạn")


class CTAConfigSchema(BaseModel):
    """CTA section configuration"""
    cta_enabled: bool = Field(default=True)
    cta_title: str = Field(default="Sẵn sàng bắt đầu?")
    cta_subtitle: str = Field(default="Tham gia cùng hàng nghìn người dùng")
    cta_button_text: str = Field(default="Đăng ký miễn phí ngay")


class TestimonialsConfigSchema(BaseModel):
    """Testimonials section configuration"""
    testimonials_enabled: bool = Field(default=True)
    testimonials_title: str = Field(default="Khách hàng nói gì?")
    testimonials_subtitle: str = Field(default="Hàng nghìn người dùng đã tin tưởng sử dụng dịch vụ của chúng tôi")
    testimonials_list: list[TestimonialItem] = Field(default_factory=list)


class FooterConfigSchema(BaseModel):
    """Footer configuration"""
    footer_brand_description: str = Field(default="Nền tảng AI Agent thông minh hàng đầu Việt Nam")
    footer_copyright: str = Field(default="© 2025 Xiaozhi AI. All rights reserved.")
    footer_address: str = Field(default="Hà Nội, Việt Nam")
    footer_social_facebook: str = Field(default="")
    footer_social_twitter: str = Field(default="")
    footer_social_linkedin: str = Field(default="")


class MenuConfigSchema(BaseModel):
    """Menu configuration"""
    menu_items: list[MenuItem] = Field(default_factory=list)


class BrandingConfigSchema(BaseModel):
    """Branding / Parent company configuration"""
    parent_company_name: str = Field(default="Bizino.AI")
    parent_company_url: str = Field(default="https://bizino.ai")
    company_badge_text: str = Field(default="by Bizino.AI")


class SolutionsConfigSchema(BaseModel):
    """Solutions section configuration (for B2B)"""
    solutions_enabled: bool = Field(default=True)
    solutions_title: str = Field(default="Giải pháp")
    solutions_subtitle: str = Field(default="Các giải pháp AI của chúng tôi")
    solutions_list: list[SolutionItem] = Field(default_factory=list)


class FAQConfigSchema(BaseModel):
    """FAQ section configuration"""
    faq_enabled: bool = Field(default=True)
    faq_title: str = Field(default="Câu hỏi thường gặp")
    faq_subtitle: str = Field(default="")
    faq_list: list[FAQItem] = Field(default_factory=list)


class HeroStatsSchema(BaseModel):
    """Hero stats configuration"""
    hero_stats: list[HeroStat] = Field(default_factory=list)


class HomeConfigSchema(BaseModel):
    """Combined home page configuration"""
    hero: HeroConfigSchema = Field(default_factory=HeroConfigSchema)
    hero_stats: HeroStatsSchema = Field(default_factory=HeroStatsSchema)
    features: FeaturesConfigSchema = Field(default_factory=FeaturesConfigSchema)
    solutions: SolutionsConfigSchema = Field(default_factory=SolutionsConfigSchema)
    pricing: PricingConfigSchema = Field(default_factory=PricingConfigSchema)
    cta: CTAConfigSchema = Field(default_factory=CTAConfigSchema)
    testimonials: TestimonialsConfigSchema = Field(default_factory=TestimonialsConfigSchema)
    faq: FAQConfigSchema = Field(default_factory=FAQConfigSchema)
    footer: FooterConfigSchema = Field(default_factory=FooterConfigSchema)
    menu: MenuConfigSchema = Field(default_factory=MenuConfigSchema)


class SiteSettingsRead(BaseModel):
    """Full site settings response"""
    web: WebConfigSchema
    payment: PaymentConfigSchema
    home: HomeConfigSchema
    branding: BrandingConfigSchema = Field(default_factory=BrandingConfigSchema)

    class Config:
        from_attributes = True


class SiteSettingsUpdate(BaseModel):
    """Update site settings request"""
    web: Optional[WebConfigSchema] = None
    payment: Optional[PaymentConfigSchema] = None
    home: Optional[HomeConfigSchema] = None
    branding: Optional[BrandingConfigSchema] = None

