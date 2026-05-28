const fs = require('fs');
const file = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/pages/admin/AdminUsersPage.tsx';
let content = fs.readFileSync(file, 'utf8');

content = content.replace(
    /type="password"[\s\S]*?placeholder="Mật khẩu"\s*\/>/,
    \`type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full rounded-md border border-slate-300 p-2 text-sm"
                placeholder="Mật khẩu"
                required
              />
              <p className="text-xs text-slate-500">
                Ít nhất 8 ký tự, gồm chữ hoa, thường, số và ký tự đặc biệt.
              </p>\`
);

fs.writeFileSync(file, content);
