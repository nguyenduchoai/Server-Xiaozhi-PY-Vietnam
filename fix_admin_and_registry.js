const fs = require('fs');

// 1. Fix AdminUsersPage.tsx client-side validation
let adminFile = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/pages/admin/AdminUsersPage.tsx';
let adminContent = fs.readFileSync(adminFile, 'utf8');

adminContent = adminContent.replace(
    /if \(pwd\.length < 8 \|\| \!\\/\[a-z\]\\/\.test\(pwd\) \|\| \!\\/\[A-Z\]\\/\.test\(pwd\) \|\| \!\\/\[0-9\]\\/\.test\(pwd\) \|\| \!\\/\[\^a-zA-Z0-9\]\\/\.test\(pwd\)\) \{/g,
    `if (pwd.length < 6) {`
);

adminContent = adminContent.replace(
    /toast\.error\("Mật khẩu không đủ mạnh\. Vui lòng kiểm tra lại yêu cầu\."\);/g,
    `toast.error("Mật khẩu phải có ít nhất 6 ký tự.");`
);

adminContent = adminContent.replace(
    /if \(newPassword\.length < 8 \|\| \!\\/\[a-z\]\\/\.test\(newPassword\) \|\| \!\\/\[A-Z\]\\/\.test\(newPassword\) \|\| \!\\/\[0-9\]\\/\.test\(newPassword\) \|\| \!\\/\[\^a-zA-Z0-9\]\\/\.test\(newPassword\)\) \{/g,
    `if (newPassword.length < 6) {`
);

adminContent = adminContent.replace(
    /setPasswordError\("Mật khẩu không đủ mạnh\. Yêu cầu có chữ hoa, thường, số và ký tự đặc biệt\."\);/g,
    `setPasswordError("Mật khẩu phải có ít nhất 6 ký tự.");`
);

adminContent = adminContent.replace(
    /placeholder="Ít nhất 8 ký tự: hoa, thường, số, đặc biệt"/g,
    `placeholder="Tối thiểu 6 ký tự"`
);

adminContent = adminContent.replace(
    /Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt\./g,
    `Mật khẩu phải có ít nhất 6 ký tự.`
);

adminContent = adminContent.replace(
    /placeholder="Tối thiểu 8 ký tự"/g,
    `placeholder="Tối thiểu 6 ký tự"`
);

fs.writeFileSync(adminFile, adminContent);

// 2. Fix schema_registry.py in backend to add Google AI Studio guide
let registryFile = '/Volumes/data/DEV2/xiaozhi-ce/backend/src/app/ai/providers/schema_registry.py';
let registryContent = fs.readFileSync(registryFile, 'utf8');

registryContent = registryContent.replace(
    /description="Gemini API key từ Google AI Studio",/g,
    `description="Lấy API Key MIỄN PHÍ tại: https://aistudio.google.com/app/apikey",`
);

fs.writeFileSync(registryFile, registryContent);

