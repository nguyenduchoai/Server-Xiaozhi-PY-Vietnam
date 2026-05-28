import { useBrand } from "@/hooks/useBrand";
import { Button } from "@douyinfe/semi-ui";
import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function TermsPage() {
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
                    Điều khoản sử dụng
                </h1>

                <div className={`prose max-w-none ${isDark ? 'prose-invert' : ''}`}>
                    <p className={`text-lg ${isDark ? 'text-gray-400' : 'text-muted-foreground'} mb-8`}>
                        Cập nhật lần cuối: 31/12/2024
                    </p>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>1. Giới thiệu</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chào mừng bạn đến với {brand.name}. Bằng việc truy cập và sử dụng dịch vụ của chúng tôi,
                            bạn đồng ý tuân thủ và chịu ràng buộc bởi các điều khoản và điều kiện sau đây.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>2. Định nghĩa</h2>
                        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-300' : ''}`}>
                            <li><strong>"Dịch vụ"</strong>: Nền tảng AI IoT và các tính năng liên quan.</li>
                            <li><strong>"Người dùng"</strong>: Cá nhân hoặc tổ chức sử dụng Dịch vụ.</li>
                            <li><strong>"Nội dung"</strong>: Dữ liệu, văn bản, hình ảnh được tạo hoặc tải lên.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>3. Quyền sử dụng</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chúng tôi cấp cho bạn quyền sử dụng cá nhân, không độc quyền, không thể chuyển nhượng
                            để truy cập và sử dụng Dịch vụ theo các điều khoản này.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>4. Nghĩa vụ của Người dùng</h2>
                        <p className={`mb-4 ${isDark ? 'text-gray-300' : ''}`}>Khi sử dụng Dịch vụ, bạn đồng ý:</p>
                        <ul className={`list-disc pl-6 space-y-2 ${isDark ? 'text-gray-300' : ''}`}>
                            <li>Không sử dụng Dịch vụ cho mục đích bất hợp pháp.</li>
                            <li>Không can thiệp vào hoạt động của Dịch vụ.</li>
                            <li>Bảo mật thông tin tài khoản của bạn.</li>
                            <li>Tuân thủ mọi quy định pháp luật hiện hành.</li>
                        </ul>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>5. Sở hữu trí tuệ</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Tất cả quyền sở hữu trí tuệ trong Dịch vụ thuộc về {brand.name} hoặc các bên cấp phép.
                            Bạn không được sao chép, sửa đổi, phân phối mà không có sự đồng ý.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>6. Giới hạn trách nhiệm</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Dịch vụ được cung cấp "nguyên trạng". Chúng tôi không chịu trách nhiệm cho bất kỳ
                            thiệt hại nào phát sinh từ việc sử dụng hoặc không thể sử dụng Dịch vụ.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>7. Thay đổi điều khoản</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Chúng tôi có quyền sửa đổi các điều khoản này bất cứ lúc nào.
                            Việc tiếp tục sử dụng Dịch vụ sau khi thay đổi được coi là chấp nhận điều khoản mới.
                        </p>
                    </section>

                    <section className="mb-12">
                        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>8. Liên hệ</h2>
                        <p className={isDark ? 'text-gray-300' : ''}>
                            Nếu bạn có câu hỏi về Điều khoản sử dụng này, vui lòng liên hệ chúng tôi qua email
                            hoặc các kênh hỗ trợ trên website.
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
