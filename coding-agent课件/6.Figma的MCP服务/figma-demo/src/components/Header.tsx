import { images } from '../assets/images';

const navItems = ['产品服务', '解决方案', '开发者', '客户案例', '支持与服务', '关于我们'];

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-white/20">
      <div className="max-w-[1440px] mx-auto px-[60px] h-[72px] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src={images.logo} alt="AI智能云" className="w-10 h-10 rounded-lg" />
          <div className="flex flex-col">
            <span className="text-base font-medium text-dark leading-tight">AI智能云</span>
            <span className="text-xs text-gray leading-tight">AI设计铺出品</span>
          </div>
        </div>

        <nav className="flex items-center gap-8">
          {navItems.map((item) => (
            <a
              key={item}
              href="#"
              className="text-base text-dark hover:text-primary transition-colors"
            >
              {item}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-4">
          <a href="#" className="text-base text-dark hover:text-primary transition-colors">
            登录
          </a>
          <button className="px-6 py-2 bg-gradient-to-r from-primary via-primary-mid to-primary-dark text-white rounded text-base hover:opacity-90 transition-opacity">
            免费试用
          </button>
        </div>
      </div>
    </header>
  );
}
