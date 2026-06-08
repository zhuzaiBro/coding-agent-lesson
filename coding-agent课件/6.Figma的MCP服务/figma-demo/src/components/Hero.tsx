import { images } from '../assets/images';

const quickLinks = [
  { icon: images.aiServiceIcon, label: '智能客服', gradient: 'from-[#3d73ff] to-[#5f8cfb]' },
  { icon: images.dataAnalysisIcon, label: '数据分析', gradient: 'from-[#0db9ff] to-[#4cbeff]' },
  { icon: images.recommendIcon, label: '智能推荐', gradient: 'from-[#00cf9f] to-[#21e1b5]' },
  { icon: images.voiceIcon, label: '语音识别', gradient: 'from-[#686fff] to-[#8266ff]' },
];

export default function Hero() {
  return (
    <section className="relative w-full h-[720px] overflow-hidden">
      <img
        src={images.heroBg}
        alt=""
        className="absolute inset-0 w-full h-full object-cover"
      />

      <div className="relative z-10 flex flex-col items-center justify-center h-full pt-[72px]">
        <h1 className="text-[64px] font-semibold leading-[1] text-center mb-2">
          <span className="text-dark">AI智能云 · </span>
          <span className="text-primary">企业服务中心</span>
        </h1>

        <div className="mt-6 px-8 py-2.5 bg-gradient-to-r from-primary via-primary-mid to-primary-dark rounded-[50px]">
          <span className="text-white text-2xl">助您专注企业发展</span>
        </div>

        <p className="mt-8 text-xl text-dark">
          依托领先的人工智能技术，为企业提供全方位智能化解决方案
        </p>

        <div className="mt-8 w-[1104px] h-[72px] bg-white/80 border-2 border-primary rounded-2xl shadow-[0px_4px_23.5px_0px_rgba(0,24,104,0.1)] flex items-center px-8">
          <span className="text-gray text-base flex-1">请输入您需要的服务或解决方案</span>
          <img src={images.searchIcon} alt="搜索" className="w-[26px] h-[26px]" />
        </div>

        <div className="mt-6 flex gap-6">
          {quickLinks.map((item) => (
            <div
              key={item.label}
              className="flex items-center gap-2.5 bg-white/80 rounded-lg px-8 py-4 hover:bg-white hover:shadow-md transition-all cursor-pointer"
            >
              <div className={`w-9 h-9 rounded-lg bg-gradient-to-b ${item.gradient} flex items-center justify-center`}>
                <img src={item.icon} alt={item.label} className="w-6 h-6" />
              </div>
              <span className="text-base text-dark">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
