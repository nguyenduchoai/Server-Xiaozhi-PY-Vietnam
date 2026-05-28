import { useBrand } from "@/hooks/useBrand";
import { Button } from "@douyinfe/semi-ui";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function PrivacyPage() {
    const brand = useBrand();
    const navigate = useNavigate();
    const isDark = brand.id === 'xiaozhi';

    return (
        <div className={`min-h-screen ${isDark ? 'bg-[#030712] text-gray-100' : 'bg-background text-foreground'}`}>
            {/* Header */}
            <header className={`sticky top-0 z-50 backdrop-blur-md border-b ${isDark ? 'bg-[#030712]/80 border-white/10' : 'bg-background/80 border-border'}`}>
                <div className="container mx-auto px-4 h-16 flex items-center justify-between">
                    <Button
                        theme="borderless"
                        onClick={() => navigate('/')}
                        className={isDark ? 'text-gray-300 hover:text-white hover:bg-white/10' : ''}
                    >
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Quay lại
                    </Button>
                    <span className="font-bold">{brand.name}</span>
                </div>
            </header>

            {/* Content */}
            <main className="container mx-auto px-4 py-16 max-w-4xl">
                <h1 className={`text-4xl font-bold mb-8 ${isDark ? 'text-white' : ''}`}>
                    Chính sách bảo mật
                </h1>

                <div className={`prose max-w-none ${isDark ? 'prose-invert' : ''}`}>
                    <p className={`text-lg ${isDark ? 'text-gray-400' : 'text-muted-foreground'} mb-8`}>
                        Cập nhật lần cuối: 31/12/2024
                    </p>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>1. Giới thiệu</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            {brand.name} cam kết bảo vệ quyền riêng tư của bạn. Chính sách này mô tả cách chúng tôi
                            thu thập, sử dụng, và bảo vệ thông tin cá nhân của bạn.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>2. Thông tin chúng tôi thu thập</h2>
                        <p className={`mb-4 ${isDark ? 'text-gray-300' : ''}`}>Chúng tôi có thể thu thập các loại thông tin sau:</p>
                        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-300' : ''}`}>
                            <li><strong>Thông tin tài khoản:</strong> Tên, email, mật khẩu (đã mã hóa).</li>
                            <li><strong>Dữ liệu sử dụng:</strong> Nhật ký hoạt động, lịch sử trò chuyện với AI.</li>
                            <li><strong>Thông tin thiết bị:</strong> MAC address, loại thiết bị IoT kết nối.</li>
                            <li><strong>Dữ liệu kỹ thuật:</strong> IP address, trình duyệt, hệ điều hành.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>3. Cách chúng tôi sử dụng thông tin</h2>
                        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-300' : ''}`}>
                            <li>Cung cấp và cải thiện Dịch vụ.</li>
                            <li>Cá nhân hóa trải nghiệm người dùng.</li>
                            <li>Gửi thông báo và cập nhật quan trọng.</li>
                            <li>Phân tích và nghiên cứu để nâng cao chất lượng.</li>
                            <li>Tuân thủ các yêu cầu pháp lý.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>4. Bảo mật dữ liệu</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chúng tôi áp dụng các biện pháp bảo mật tiêu chuẩn ngành để bảo vệ dữ liệu của bạn:
                        </p>
                        <ul className={`list-disc pl-6 space-y-2 mt-4 ${isDark ? 'text-gray-300' : ''}`}>
                            <li>Mã hóa SSL/TLS cho mọi kết nối.</li>
                            <li>Mã hóa mật khẩu bằng bcrypt.</li>
                            <li>Xác thực JWT với token bảo mật.</li>
                            <li>Giám sát và phát hiện xâm nhập 24/7.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>5. Chia sẻ thông tin</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chúng tôi <strong>không bán</strong> thông tin cá nhân của bạn. Chúng tôi chỉ chia sẻ dữ liệu khi:
                        </p>
                        <ul className={`list-disc pl-6 space-y-2 mt-4 ${isDark ? 'text-gray-300' : ''}`}>
                            <li>Được bạn đồng ý.</li>
                            <li>Cần thiết để cung cấp Dịch vụ (với đối tác xử lý).</li>
                            <li>Theo yêu cầu của pháp luật.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>6. Quyền của bạn</h2>
                        <p className={`mb-4 ${isDark ? 'text-gray-300' : ''}`}>Bạn có quyền:</p>
                        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-300' : ''}`}>
                            <li>Truy cập và xem dữ liệu cá nhân của bạn.</li>
                            <li>Yêu cầu chỉnh sửa thông tin không chính xác.</li>
                            <li>Yêu cầu xóa tài khoản và dữ liệu.</li>
                            <li>Xuất dữ liệu của bạn.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>7. Cookie và công nghệ theo dõi</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chúng tôi sử dụng cookies để cải thiện trải nghiệm người dùng, lưu trữ tùy chọn,
                            và phân tích lưu lượng truy cập. Bạn có thể kiểm soát cookies qua cài đặt trình duyệt.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>8. Lưu trữ dữ liệu</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Dữ liệu của bạn được lưu trữ trên máy chủ tại Việt Nam và có thể được sao lưu tại
                            các trung tâm dữ liệu đối tác để đảm bảo tính liên tục của Dịch vụ.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>9. Thay đổi chính sách</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chúng tôi có thể cập nhật Chính sách bảo mật này theo thời gian.
                            Các thay đổi quan trọng sẽ được thông báo qua email hoặc trên website.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>10. Liên hệ</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Nếu bạn có câu hỏi về Chính sách bảo mật này hoặc muốn thực hiện quyền của mình,
                            vui lòng liên hệ chúng tôi qua email hoặc các kênh hỗ trợ trên website.
                        </p>
                    </section>
                </div>
            </main>

            {/* Footer */}
            <footer className={`border-t py-8 ${isDark ? 'border-white/10 bg-[#030712]' : 'bg-muted/50'}`}>
                <div className="container mx-auto px-4 text-center">
                    <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-muted-foreground'}`}>
                        © 2024 {brand.name}. All rights reserved.
                    </p>
                </div>
            </footer>
        </div>
    );
}
