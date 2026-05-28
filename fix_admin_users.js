const fs = require('fs');

let file = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/pages/admin/AdminUsersPage.tsx';
let content = fs.readFileSync(file, 'utf8');

// Restore handlePasswordReset properly
content = content.replace(
    /const handlePasswordReset = async \(\) => \{\n      const result = await adminApi\.resetUserPassword\(passwordUser\.id, newPassword\);/g,
    `const handlePasswordReset = async () => {
    if (!passwordUser) return;

    setPasswordError("");
    setPasswordSuccess("");

    if (!newPassword || newPassword.length < 6) {
      setPasswordError("Mật khẩu phải có ít nhất 6 ký tự");
      return;
    }

    setProcessing(true);
    try {
      const result = await adminApi.resetUserPassword(passwordUser.id, newPassword);`
);

// We had some other bad replacement in the render logic?
// No, the other chunks seemed fine. But let's check if the second chunk broke anything.
// chunk 3: Target was `if (newPassword.length < 8 ...` which I just restored.

fs.writeFileSync(file, content);
