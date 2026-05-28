const fs = require('fs');
let file = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/pages/admin/AdminUsersPage.tsx';
let content = fs.readFileSync(file, 'utf8');

// Add hint below password in Create User
content = content.replace(
    /placeholder="Ít nhất 8 ký tự: hoa, thường, số, đặc biệt"\s*\/>\s*<\/div>/g,
    `placeholder="Ít nhất 8 ký tự: hoa, thường, số, đặc biệt"
            />
            <Text type="secondary" size="small" style={{ display: 'block', marginTop: 4 }}>
              Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt.
            </Text>
          </div>`
);

// Add hint below password in Reset Password
content = content.replace(
    /placeholder="Tối thiểu 8 ký tự"\s*size="large"\s*\/>\s*<\/div>/g,
    `placeholder="Tối thiểu 8 ký tự"
                  size="large"
                />
                <Text type="secondary" size="small" style={{ display: 'block', marginTop: 4 }}>
                  Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt.
                </Text>
              </div>`
);

// Add client side validation
const validationLogic = `
    const pwd = createForm.password;
    if (pwd.length < 8 || !/[a-z]/.test(pwd) || !/[A-Z]/.test(pwd) || !/[0-9]/.test(pwd) || !/[^a-zA-Z0-9]/.test(pwd)) {
      toast.error("Mật khẩu không đủ mạnh. Vui lòng kiểm tra lại yêu cầu.");
      return;
    }
`;

content = content.replace(
    /if \(\!createForm\.name \|\| \!createForm\.email \|\| \!createForm\.password\) \{/,
    `if (!createForm.name || !createForm.email || !createForm.password) {`
);

content = content.replace(
    /toast\.error\("Vui lòng điền đầy đủ thông tin"\);\s*return;\s*\}/,
    `toast.error("Vui lòng điền đầy đủ thông tin");
      return;
    }
${validationLogic}`
);

// And for reset password validation
const resetValidationLogic = `
    if (newPassword.length < 8 || !/[a-z]/.test(newPassword) || !/[A-Z]/.test(newPassword) || !/[0-9]/.test(newPassword) || !/[^a-zA-Z0-9]/.test(newPassword)) {
      setPasswordError("Mật khẩu không đủ mạnh. Yêu cầu có chữ hoa, thường, số và ký tự đặc biệt.");
      return;
    }
`;

content = content.replace(
    /if \(\!newPassword\) \{\s*setPasswordError\("Vui lòng nhập mật khẩu mới"\);\s*return;\s*\}/,
    `if (!newPassword) {
      setPasswordError("Vui lòng nhập mật khẩu mới");
      return;
    }
${resetValidationLogic}`
);

fs.writeFileSync(file, content);
