const fs = require('fs');
const file = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/pages/admin/AdminUsersPage.tsx';
let content = fs.readFileSync(file, 'utf8');

const replacement = `      const detail = error.response?.data?.detail;
      let errMsg = "Không thể tạo người dùng";
      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errMsg = detail[0].msg;
      }
      toast.error(errMsg);`;

content = content.replace(/toast\.error\(error\.response\?\.data\?\.detail \|\| "Không thể tạo người dùng"\);/, replacement);

const replacementReset = `      const detail = error.response?.data?.detail;
      let errMsg = "Không thể đặt lại mật khẩu";
      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errMsg = detail[0].msg;
      }
      setPasswordError(errMsg);`;

content = content.replace(/setPasswordError\(error\.response\?\.data\?\.detail \|\| "Không thể đặt lại mật khẩu"\);/, replacementReset);

content = content.replace(/placeholder="Tối thiểu 8 ký tự"/, 'placeholder="Ít nhất 8 ký tự: hoa, thường, số, đặc biệt"');
content = content.replace(/placeholder="Ví dụ: \*\*\*\*\*\*\*\*"/, 'placeholder="Mật khẩu: Ít nhất 8 ký tự, gồm chữ hoa, thường, số, đặc biệt"');

fs.writeFileSync(file, content);
