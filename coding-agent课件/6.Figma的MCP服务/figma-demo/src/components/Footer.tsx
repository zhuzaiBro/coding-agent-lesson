import { images } from '../assets/images';

const footerSections = [
  {
    title: '产品服务',
    links: ['机器学习', '智能对话', '计算机视觉', '数据智能', '语音识别', '知识图谱'],
  },
  {
    title: '解决方案',
    links: ['智能客服', '数据分析', '智能推荐', '风险控制', '营销优化', '供应链管理'],
  },
  {
    title: '开发者',
    links: ['API文档', 'SDK下载', '示例代码', '技术博客', '开发者社区', '在线调试'],
  },
  {
    title: '关于我们',
    links: ['公司介绍', '新闻动态', '加入我们', '联系我们', '合作伙伴', '投资者关系'],
  },
  {
    title: '支持与服务',
    links: ['帮助中心', '服务协议', '隐私政策', '安全中心', '备案号', '客户支持'],
  },
];

export default function Footer() {
  return (
    <footer className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-[#000a22] to-black" />
      <img src={images.footerBg} alt="" className="absolute inset-0 w-full h-full object-cover opacity-30" />

      <div className="relative z-10 max-w-[1440px] mx-auto px-[60px] py-16">
        <div className="grid grid-cols-6 gap-8">
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              <img src={images.logo} alt="AI智能云" className="w-[30px] h-[30px] rounded-md" />
              <span className="text-xl text-white">AI智能云</span>
            </div>
            <p className="text-sm text-[#99a1af] leading-5">
              领先的企业级人工智能服务平台
            </p>
            <div className="flex gap-4 mt-2">
              {Object.values(images.socialIcons).map((icon, i) => (
                <a key={i} href="#" className="w-5 h-5 opacity-60 hover:opacity-100 transition-opacity">
                  <img src={icon} alt="" className="w-full h-full" />
                </a>
              ))}
            </div>
          </div>

          {footerSections.map((section) => (
            <div key={section.title} className="flex flex-col gap-4">
              <h3 className="text-lg text-white">{section.title}</h3>
              <ul className="flex flex-col gap-2">
                {section.links.map((link) => (
                  <li key={link}>
                    <a href="#" className="text-sm text-[#d1d5dc] hover:text-white transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 pt-8 border-t border-[#1e2939] flex items-center justify-between">
          <p className="text-sm text-[#bfcbe0]">© 2025 AI智能云. 保留所有权利.</p>
          <div className="flex gap-6">
            <a href="#" className="text-sm text-[#e4eaf4] hover:text-white transition-colors">服务条款</a>
            <a href="#" className="text-sm text-[#e4eaf4] hover:text-white transition-colors">隐私政策</a>
            <a href="#" className="text-sm text-[#e4eaf4] hover:text-white transition-colors">Cookie设置</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
