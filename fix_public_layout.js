const fs = require('fs');
const file = '/Volumes/data/DEV2/xiaozhi-ce/frontend/src/App.tsx';
let content = fs.readFileSync(file, 'utf8');

const newHeader = `<header className="sticky top-0 z-50 bg-white/70 backdrop-blur-xl border-b border-slate-200 shadow-sm transition-all">
      <div className="container mx-auto px-4 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
              <Link to="/" className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-violet-600 to-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-md shadow-violet-500/20">X</div>
                  <span className="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">XiaoZhi AI IoT</span>
              </Link>
          </div>

          <nav className="hidden lg:flex items-center gap-8">
              <Link to="/#features" className="text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">Tính năng</Link>
              <Link to="/#installation" className="text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">Triển khai</Link>
              <Link to="/#faq" className="text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">Hỏi đáp</Link>
              
              <span className="w-px h-5 bg-slate-200"></span>

              <Link to="/asset-generator" className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">
                  <Wand2 className="w-3.5 h-3.5" />Assets
              </Link>
              <Link to="/tools/flasher" className="flex items-center gap-1.5 text-sm font-semibold text-slate-600 hover:text-violet-700 transition-colors">
                  <Download className="w-3.5 h-3.5" />Flasher
              </Link>
          </nav>

          <div className="flex items-center gap-4">
              <Link to="/login" className="hidden sm:block">
                  <button className="h-10 px-4 py-2 inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 text-slate-600 hover:text-violet-700 hover:bg-violet-50">Đăng nhập</button>
              </Link>
              <Link to="/login">
              <button className="h-10 inline-flex items-center justify-center whitespace-nowrap font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-gradient-to-r from-violet-600 to-indigo-600 text-white hover:from-violet-700 hover:to-indigo-700 rounded-full px-6 shadow-md shadow-violet-600/20 border border-violet-500/50">
                  Bắt đầu tạo AI
              </button>
              </Link>
          </div>
      </div>
    </header>`;

const oldHeaderRegex = /<header className="sticky top-0 z-50 bg-white\/70 backdrop-blur-xl border-b border-slate-200 shadow-sm">[\s\S]*?<\/header>/;
content = content.replace(oldHeaderRegex, newHeader);

// In App.tsx, button is not imported, so we just used native HTML <button> instead of <Button>.
// It should work.

fs.writeFileSync(file, content);
