"""
Email Service for sending emails via SMTP (Gmail, etc.)

Features:
- Send password reset emails
- Send welcome emails
- Template-based email rendering
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime, timedelta, timezone
import jwt
import os

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""

    def __init__(
        self,
        host: str = "smtp.gmail.com",
        port: int = 587,
        username: str = "",
        password: str = "",
        from_email: str = "",
        from_name: str = "Xiaozhi AI",
        use_tls: bool = True,
        enabled: bool = False,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email or username
        self.from_name = from_name
        self.use_tls = use_tls
        self.enabled = enabled
        
        # JWT secret for tokens
        secret = os.getenv("SECRET_KEY")
        if not secret:
            raise ValueError("SECRET_KEY is utterly missing")
        self.secret_key = secret

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        Send an email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text body content (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email service is disabled. Enable it in settings.")
            return False

        if not self.username or not self.password:
            logger.error("SMTP credentials not configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            # Attach text and HTML parts
            if text_content:
                part1 = MIMEText(text_content, "plain", "utf-8")
                msg.attach(part1)
            
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part2)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def generate_password_reset_token(
        self, 
        user_id: str, 
        email: str,
        expire_minutes: int = 30
    ) -> str:
        """
        Generate a JWT token for password reset
        
        Args:
            user_id: User's ID
            email: User's email
            expire_minutes: Token expiry in minutes
            
        Returns:
            JWT token string
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "password_reset",
            "exp": expire,
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return token

    def verify_password_reset_token(self, token: str) -> Optional[dict]:
        """
        Verify a password reset token
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if payload.get("type") != "password_reset":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Password reset token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid password reset token: {e}")
            return None

    def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_link: str,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """
        Send a password reset email
        
        Args:
            to_email: Recipient email
            user_name: User's display name
            reset_link: Full URL for password reset page
            app_name: Application name for branding
            
        Returns:
            True if sent successfully
        """
        subject = f"[{app_name}] Đặt lại mật khẩu"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #667eea; color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .button:hover {{ background: #5a6fd6; }}
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 20px; }}
                .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Đặt Lại Mật Khẩu</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn tại <strong>{app_name}</strong>.</p>
                    <p>Nhấn vào nút bên dưới để đặt mật khẩu mới:</p>
                    
                    <center>
                        <a href="{reset_link}" class="button">Đặt Lại Mật Khẩu</a>
                    </center>
                    
                    <div class="warning">
                        <strong>⚠️ Lưu ý:</strong> Link này sẽ hết hạn sau 30 phút.
                    </div>
                    
                    <p>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.</p>
                    
                    <p>Nếu nút không hoạt động, copy và paste link sau vào trình duyệt:</p>
                    <p style="word-break: break-all; color: #667eea;">{reset_link}</p>
                </div>
                <div class="footer">
                    <p>© 2024 {app_name}. All rights reserved.</p>
                    <p>Email này được gửi tự động, vui lòng không reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Xin chào {user_name},

        Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn tại {app_name}.

        Truy cập link sau để đặt mật khẩu mới:
        {reset_link}

        Link này sẽ hết hạn sau 30 phút.

        Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.

        ---
        {app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

    def send_friend_invitation_email(
        self,
        to_email: str,
        sender_name: str,
        invite_link: str,
        message: Optional[str] = None,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """
        Send a friend invitation email
        
        Args:
            to_email: Recipient email
            sender_name: Name of the person inviting
            invite_link: Full URL for accepting invitation
            message: Optional personal message
            app_name: Application name for branding
            
        Returns:
            True if sent successfully
        """
        subject = f"[{app_name}] {sender_name} muốn kết bạn với bạn!"
        
        personal_msg = f'<p style="background: #e8f4fd; padding: 15px; border-radius: 8px; font-style: italic;">"{message}"</p>' if message else ""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; background: #4facfe; color: white; padding: 14px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .button:hover {{ background: #3d9cee; }}
                .footer {{ text-align: center; color: #888; font-size: 12px; margin-top: 20px; }}
                .highlight {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>👋 Lời Mời Kết Bạn</h1>
                </div>
                <div class="content">
                    <p>Xin chào!</p>
                    <p><strong>{sender_name}</strong> muốn kết bạn với bạn trên <strong>{app_name}</strong>!</p>
                    
                    {personal_msg}
                    
                    <p>Với tính năng Bạn Bè, bạn có thể:</p>
                    <ul>
                        <li>🎤 Gọi Intercom xuyên tài khoản</li>
                        <li>💬 Gửi tin nhắn voice chat</li>
                        <li>🔔 Nhận thông báo từ bạn bè</li>
                    </ul>
                    
                    <center>
                        <a href="{invite_link}" class="button">Chấp Nhận Lời Mời</a>
                    </center>
                    
                    <div class="highlight">
                        <strong>💡 Lưu ý:</strong> Link này sẽ hết hạn sau 7 ngày.
                    </div>
                    
                    <p>Nếu nút không hoạt động, copy và paste link sau vào trình duyệt:</p>
                    <p style="word-break: break-all; color: #4facfe;">{invite_link}</p>
                </div>
                <div class="footer">
                    <p>© 2026 {app_name}. All rights reserved.</p>
                    <p>Nếu bạn không quen {sender_name}, bạn có thể bỏ qua email này.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Xin chào!

        {sender_name} muốn kết bạn với bạn trên {app_name}!
        
        {f'Tin nhắn: "{message}"' if message else ''}

        Truy cập link sau để chấp nhận lời mời:
        {invite_link}

        Link này sẽ hết hạn sau 7 ngày.

        ---
        {app_name}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

    # ------------------------------------------------------------------
    # Payment-approval / rejection / welcome emails
    # Used by:
    #   - admin.approve_payment (manual review by SuperAdmin)
    #   - auth.register (welcome email on new account)
    # Failures here must NEVER abort the surrounding flow — callers wrap
    # these in try/except and treat email as best-effort.
    # ------------------------------------------------------------------

    def send_payment_approved_email(
        self,
        to_email: str,
        user_name: str,
        plan_name: str,
        amount: int,
        billing_cycle: str,
        expires_at: Optional[datetime] = None,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """Notify user that their manually-submitted payment was approved."""
        subject = f"[{app_name}] ✅ Thanh toán đã được duyệt - Gói {plan_name}"

        cycle_label = "1 năm" if billing_cycle == "yearly" else "1 tháng"
        expires_str = (
            expires_at.strftime("%d/%m/%Y") if expires_at else "Theo gói đăng ký"
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                           color: white; padding: 30px; text-align: center;
                           border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px;
                           border-radius: 0 0 10px 10px; }}
                .success-icon {{ font-size: 48px; }}
                .details {{ background: white; padding: 20px; border-radius: 8px;
                           margin: 20px 0; border-left: 4px solid #10b981; }}
                .footer {{ text-align: center; color: #888; font-size: 12px;
                          margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">✅</div>
                    <h1>Thanh Toán Được Duyệt!</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Yêu cầu thanh toán của bạn đã được quản trị viên xác minh
                       và duyệt thành công. Gói dịch vụ đã được kích hoạt ngay.</p>

                    <div class="details">
                        <p><strong>Chi tiết:</strong></p>
                        <ul>
                            <li>Gói dịch vụ: <strong>{plan_name}</strong></li>
                            <li>Chu kỳ: <strong>{cycle_label}</strong></li>
                            <li>Số tiền: <strong>{amount:,} VND</strong></li>
                            <li>Hết hạn: <strong>{expires_str}</strong></li>
                        </ul>
                    </div>

                    <p>Bạn có thể đăng nhập và sử dụng đầy đủ tính năng ngay bây giờ.</p>
                    <p>Cảm ơn bạn đã tin dùng dịch vụ!</p>
                </div>
                <div class="footer">
                    <p>© {app_name}. All rights reserved.</p>
                    <p>Email này được gửi tự động, vui lòng không reply.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = (
            f"Xin chào {user_name},\n\n"
            f"Thanh toán của bạn cho gói {plan_name} ({cycle_label}, "
            f"{amount:,} VND) đã được duyệt và kích hoạt.\n"
            f"Hết hạn: {expires_str}\n\n"
            f"---\n{app_name}"
        )

        return self.send_email(to_email, subject, html_content, text_content)

    def send_payment_rejected_email(
        self,
        to_email: str,
        user_name: str,
        plan_name: str,
        amount: int,
        reason: Optional[str] = None,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """Notify user that their payment request was rejected."""
        subject = f"[{app_name}] ❌ Thanh toán không được duyệt - Gói {plan_name}"

        reason_html = (
            f'<div style="background:#fff3cd;border-left:4px solid #ffc107;'
            f'padding:12px 16px;margin:16px 0;border-radius:4px;">'
            f"<strong>Lý do:</strong> {reason}</div>"
            if reason
            else ""
        )
        reason_text = f"Lý do: {reason}\n\n" if reason else ""

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
                           color: white; padding: 30px; text-align: center;
                           border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px;
                           border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; color: #888; font-size: 12px;
                          margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size:48px;">⚠️</div>
                    <h1>Thanh Toán Không Được Duyệt</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Yêu cầu thanh toán của bạn cho gói <strong>{plan_name}</strong>
                       ({amount:,} VND) đã <strong>không được duyệt</strong>
                       sau khi quản trị viên kiểm tra.</p>

                    {reason_html}

                    <p>Số tiền chuyển khoản (nếu có) sẽ được hoàn lại theo quy trình
                       hỗ trợ. Vui lòng liên hệ với chúng tôi nếu bạn cho rằng đây
                       là nhầm lẫn, hoặc gửi lại yêu cầu thanh toán mới với chứng từ
                       chính xác.</p>
                </div>
                <div class="footer">
                    <p>© {app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = (
            f"Xin chào {user_name},\n\n"
            f"Yêu cầu thanh toán của bạn cho gói {plan_name} "
            f"({amount:,} VND) đã không được duyệt.\n\n"
            f"{reason_text}"
            f"Vui lòng liên hệ hỗ trợ nếu cần làm rõ.\n\n"
            f"---\n{app_name}"
        )

        return self.send_email(to_email, subject, html_content, text_content)

    def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        plan_name: str = "FREE",
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """Welcome email sent right after a user finishes /auth/register."""
        subject = f"[{app_name}] 👋 Chào mừng bạn đến với {app_name}!"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                           color: white; padding: 30px; text-align: center;
                           border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px;
                           border-radius: 0 0 10px 10px; }}
                .features {{ background: white; padding: 20px; border-radius: 8px;
                           margin: 20px 0; border-left: 4px solid #6366f1; }}
                .footer {{ text-align: center; color: #888; font-size: 12px;
                          margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size:48px;">🎉</div>
                    <h1>Chào mừng đến với {app_name}!</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Tài khoản của bạn đã được tạo thành công và đã được kích hoạt
                       gói <strong>{plan_name}</strong> miễn phí.</p>

                    <div class="features">
                        <p><strong>Bạn có thể bắt đầu với:</strong></p>
                        <ul>
                            <li>📱 Đăng ký thiết bị Xiaozhi đầu tiên</li>
                            <li>🤖 Tuỳ chỉnh agent AI (LLM, TTS, prompt)</li>
                            <li>🧠 Xây dựng kho tri thức cá nhân</li>
                            <li>👥 Mời bạn bè để gọi Intercom xuyên thiết bị</li>
                        </ul>
                    </div>

                    <p>Có câu hỏi? Đừng ngại liên hệ — chúng tôi luôn sẵn sàng hỗ trợ.</p>
                    <p>Chúc bạn có trải nghiệm tuyệt vời!</p>
                </div>
                <div class="footer">
                    <p>© {app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = (
            f"Xin chào {user_name},\n\n"
            f"Chào mừng đến với {app_name}! Tài khoản của bạn đã được tạo "
            f"thành công và đã có gói {plan_name} miễn phí đang hoạt động.\n\n"
            f"Bắt đầu bằng cách đăng ký thiết bị, tuỳ chỉnh agent AI hoặc "
            f"xây dựng kho tri thức cá nhân.\n\n"
            f"---\n{app_name}"
        )

        return self.send_email(to_email, subject, html_content, text_content)

    # ------------------------------------------------------------------
    # Notifications driven by scheduled jobs / event hooks
    #   - subscription expiry reminder (3-day cron, in subscription_maintenance)
    #   - device offline alert (24h cron, in scheduler_service)
    #   - device transferred (event hook in admin.transfer_device)
    # All best-effort: callers wrap in try/except.
    # ------------------------------------------------------------------

    def send_subscription_expiry_reminder_email(
        self,
        to_email: str,
        user_name: str,
        plan_name: str,
        expires_at: datetime,
        days_remaining: int,
        renew_url: Optional[str] = None,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """3-day reminder before a paid subscription expires."""
        subject = f"[{app_name}] ⏰ Gói {plan_name} của bạn sắp hết hạn"

        expires_str = expires_at.strftime("%d/%m/%Y")
        renew_button = (
            f'<center><a href="{renew_url}" '
            f'style="display:inline-block;background:#f59e0b;color:white;'
            f'padding:14px 30px;text-decoration:none;border-radius:5px;'
            f'margin:20px 0;">Gia hạn ngay</a></center>'
            if renew_url
            else ""
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                           color: white; padding: 30px; text-align: center;
                           border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px;
                           border-radius: 0 0 10px 10px; }}
                .details {{ background: white; padding: 20px; border-radius: 8px;
                           margin: 20px 0; border-left: 4px solid #f59e0b; }}
                .footer {{ text-align: center; color: #888; font-size: 12px;
                          margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size:48px;">⏰</div>
                    <h1>Gói Sắp Hết Hạn</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Chúng tôi xin nhắc bạn rằng gói dịch vụ
                       <strong>{plan_name}</strong> sẽ <strong>hết hạn trong
                       {days_remaining} ngày</strong> (vào {expires_str}).</p>

                    <div class="details">
                        <p><strong>Sau khi hết hạn:</strong></p>
                        <ul>
                            <li>Tài khoản sẽ tự động chuyển về gói FREE</li>
                            <li>Một số tính năng nâng cao có thể bị giới hạn</li>
                            <li>Lịch sử và dữ liệu của bạn vẫn được giữ nguyên</li>
                        </ul>
                    </div>

                    <p>Để tiếp tục sử dụng đầy đủ tính năng, vui lòng gia hạn
                       trước ngày <strong>{expires_str}</strong>.</p>

                    {renew_button}

                    <p>Nếu bạn không muốn gia hạn, không cần làm gì cả — hệ thống
                       sẽ tự động chuyển về gói FREE.</p>
                </div>
                <div class="footer">
                    <p>© {app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = (
            f"Xin chào {user_name},\n\n"
            f"Gói {plan_name} của bạn sẽ hết hạn trong {days_remaining} ngày "
            f"(vào {expires_str}).\n\n"
            f"Sau khi hết hạn, tài khoản sẽ tự chuyển về gói FREE và một số "
            f"tính năng nâng cao sẽ bị giới hạn.\n\n"
            f"{('Gia hạn tại: ' + renew_url) if renew_url else ''}\n\n"
            f"---\n{app_name}"
        )

        return self.send_email(to_email, subject, html_content, text_content)

    def send_device_offline_alert_email(
        self,
        to_email: str,
        user_name: str,
        device_name: str,
        mac_address: str,
        last_seen: Optional[datetime] = None,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """Alert sent when a device has been offline for >24h."""
        subject = f"[{app_name}] 📡 Thiết bị {device_name} đang offline"

        last_seen_str = (
            last_seen.strftime("%d/%m/%Y %H:%M UTC") if last_seen else "không rõ"
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
                           color: white; padding: 30px; text-align: center;
                           border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px;
                           border-radius: 0 0 10px 10px; }}
                .details {{ background: white; padding: 20px; border-radius: 8px;
                           margin: 20px 0; border-left: 4px solid #6b7280; }}
                .checklist {{ background: #fef3c7; border-left: 4px solid #f59e0b;
                              padding: 12px 16px; margin: 16px 0; border-radius: 4px; }}
                .footer {{ text-align: center; color: #888; font-size: 12px;
                          margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size:48px;">📡</div>
                    <h1>Thiết Bị Đang Offline</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Hệ thống phát hiện thiết bị của bạn đã <strong>offline
                       hơn 24 giờ</strong>:</p>

                    <div class="details">
                        <ul>
                            <li>Tên thiết bị: <strong>{device_name}</strong></li>
                            <li>MAC: <code>{mac_address}</code></li>
                            <li>Lần kết nối cuối: <strong>{last_seen_str}</strong></li>
                        </ul>
                    </div>

                    <div class="checklist">
                        <strong>💡 Vui lòng kiểm tra:</strong>
                        <ul>
                            <li>Thiết bị có cắm điện không?</li>
                            <li>WiFi tại nhà có hoạt động không?</li>
                            <li>Đèn báo trên thiết bị có sáng không?</li>
                            <li>Reset thiết bị (giữ nút BOOT 5 giây) nếu vẫn không kết nối</li>
                        </ul>
                    </div>

                    <p>Nếu thiết bị vẫn không hoạt động sau khi kiểm tra, vui lòng
                       liên hệ với chúng tôi để được hỗ trợ.</p>
                </div>
                <div class="footer">
                    <p>© {app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = (
            f"Xin chào {user_name},\n\n"
            f"Thiết bị {device_name} (MAC: {mac_address}) đã offline hơn 24 giờ.\n"
            f"Lần kết nối cuối: {last_seen_str}\n\n"
            f"Vui lòng kiểm tra nguồn điện, WiFi và reset thiết bị nếu cần.\n\n"
            f"---\n{app_name}"
        )

        return self.send_email(to_email, subject, html_content, text_content)

    def send_device_transferred_email(
        self,
        to_email: str,
        user_name: str,
        device_name: str,
        mac_address: str,
        from_user_email: Optional[str] = None,
        app_name: str = "Xiaozhi AI",
    ) -> bool:
        """Notify the new owner when an admin transfers a device to them."""
        subject = f"[{app_name}] 🔁 Bạn vừa nhận thiết bị mới: {device_name}"

        from_clause = (
            f"<p>Người chuyển: <strong>{from_user_email}</strong></p>"
            if from_user_email
            else ""
        )
        from_text = (
            f"Người chuyển: {from_user_email}\n" if from_user_email else ""
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                           color: white; padding: 30px; text-align: center;
                           border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px;
                           border-radius: 0 0 10px 10px; }}
                .details {{ background: white; padding: 20px; border-radius: 8px;
                           margin: 20px 0; border-left: 4px solid #06b6d4; }}
                .footer {{ text-align: center; color: #888; font-size: 12px;
                          margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div style="font-size:48px;">🔁</div>
                    <h1>Thiết Bị Mới</h1>
                </div>
                <div class="content">
                    <p>Xin chào <strong>{user_name}</strong>,</p>
                    <p>Một thiết bị vừa được chuyển sang tài khoản của bạn:</p>

                    <div class="details">
                        <ul>
                            <li>Tên thiết bị: <strong>{device_name}</strong></li>
                            <li>MAC: <code>{mac_address}</code></li>
                        </ul>
                        {from_clause}
                    </div>

                    <p>Bạn có thể quản lý thiết bị này (đổi tên, gán agent, cấu hình...)
                       trong mục <strong>Devices</strong> của tài khoản.</p>

                    <p style="background:#fef3c7;border-left:4px solid #f59e0b;
                              padding:12px 16px;border-radius:4px;">
                        <strong>⚠️ Nếu bạn không yêu cầu việc này:</strong> Vui lòng
                        liên hệ với chúng tôi ngay để xác minh — có thể có nhầm lẫn
                        từ phía quản trị viên.
                    </p>
                </div>
                <div class="footer">
                    <p>© {app_name}. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = (
            f"Xin chào {user_name},\n\n"
            f"Một thiết bị vừa được chuyển sang tài khoản của bạn:\n"
            f"- Tên: {device_name}\n"
            f"- MAC: {mac_address}\n"
            f"{from_text}\n"
            f"Quản lý thiết bị tại mục Devices.\n"
            f"Nếu không phải bạn yêu cầu, vui lòng liên hệ hỗ trợ ngay.\n\n"
            f"---\n{app_name}"
        )

        return self.send_email(to_email, subject, html_content, text_content)


# Singleton instance (will be initialized in main.py)
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the global EmailService instance"""
    global _email_service
    if _email_service is None:
        # Create with default settings (will be configured in main.py)
        _email_service = EmailService()
    return _email_service


def init_email_service(
    host: str = "smtp.gmail.com",
    port: int = 587,
    username: str = "",
    password: str = "",
    from_email: str = "",
    from_name: str = "Xiaozhi AI",
    use_tls: bool = True,
    enabled: bool = False,
) -> EmailService:
    """Initialize the global EmailService instance"""
    global _email_service
    _email_service = EmailService(
        host=host,
        port=port,
        username=username,
        password=password,
        from_email=from_email,
        from_name=from_name,
        use_tls=use_tls,
        enabled=enabled,
    )
    logger.info(f"Email service initialized (enabled={enabled})")
    return _email_service
