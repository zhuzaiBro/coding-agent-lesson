import { useState } from 'react';
import { images } from '../assets/images';

const tabs = ['全部方案', '智能客服', '数据分析', '图像识别', '语音处理', '智能推荐'];

const solutions = [
  {
    title: '智能客服解决方案',
    desc: '基于自然语言处理技术，打造7x24小时智能客服系统',
    features: ['多轮对话能力', '意图识别准确率>95%', '支持多渠道接入', '智能工单系统'],
    image: images.solutionImage1,
    gradient: 'from-[#bff0ff] to-[#73b5ff]',
    linkColor: 'text-[#155dfc]',
    position: 'left' as const,
  },
  {
    title: '数据智能分析平台',
    desc: '强大的数据处理与分析能力，助力企业洞察商业价值',
    features: ['实时数据分析', '可视化报表', '预测性分析', '自动化报告生成'],
    image: images.solutionImage2,
    gradient: 'from-[#d9daff] to-[#9490ff]',
    linkColor: 'text-[#6969ff]',
    position: 'right' as const,
  },
];

export default function Solutions() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <section className="relative py-20 overflow-hidden">
      <div
        className="absolute inset-0"
        style={{ backgroundImage: 'linear-gradient(110deg, #e1f0ff 2%, #d2e9ff 100%)' }}
      />
      <img src={images.solutionBg} alt="" className="absolute inset-0 w-full h-full object-cover" />

      <div className="relative z-10 max-w-[1440px] mx-auto px-[60px]">
        <h2 className="text-[40px] font-medium text-dark text-center leading-[52px]">
          专业精选定制解决企业发展
        </h2>

        <div className="mt-10 flex justify-center">
          <div className="bg-[#cfe6fe] border border-white rounded-full p-1 flex gap-0">
            {tabs.map((tab, i) => (
              <button
                key={tab}
                onClick={() => setActiveTab(i)}
                className={`px-8 py-3 rounded-full text-xl transition-all ${
                  i === activeTab
                    ? 'bg-white text-primary shadow-sm'
                    : 'text-dark hover:text-primary'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-10 grid grid-cols-2 gap-[26px]">
          {solutions.map((solution) => (
            <div key={solution.title} className="flex flex-col gap-[26px]">
              {solution.position === 'left' ? (
                <>
                  <div
                    className={`rounded-2xl p-[60px] relative overflow-hidden h-[386px] bg-gradient-to-br ${solution.gradient}`}
                  >
                    <div className="flex gap-8">
                      <div className="flex-1">
                        <h3 className="text-[32px] font-medium text-dark">{solution.title}</h3>
                        <p className="text-base text-dark mt-2">{solution.desc}</p>
                        <ul className="mt-8 space-y-2">
                          {solution.features.map((f) => (
                            <li key={f} className="flex items-center gap-3 text-base text-dark">
                              <img src={images.checkIcon} alt="" className="w-5 h-5" />
                              {f}
                            </li>
                          ))}
                        </ul>
                        <a href="#" className={`mt-8 inline-flex items-center gap-2 ${solution.linkColor} text-base`}>
                          了解更多
                          <img src={images.arrowIcon} alt="" className="w-5 h-5" />
                        </a>
                      </div>
                      <img src={solution.image} alt={solution.title} className="w-[319px] h-[319px] object-contain" />
                    </div>
                  </div>
                  <div className="rounded-2xl overflow-hidden h-[386px]">
                    <img src={images.solutionCardBg} alt="" className="w-full h-full object-cover" />
                  </div>
                </>
              ) : (
                <>
                  <div className="rounded-2xl overflow-hidden h-[386px]">
                    <img src={images.solutionCardBg2} alt="" className="w-full h-full object-cover" />
                  </div>
                  <div
                    className={`rounded-2xl p-[60px] relative overflow-hidden h-[386px] bg-gradient-to-br ${solution.gradient}`}
                  >
                    <div className="flex gap-8">
                      <div className="flex-1">
                        <h3 className="text-[32px] font-medium text-dark">{solution.title}</h3>
                        <p className="text-base text-dark mt-2">{solution.desc}</p>
                        <ul className="mt-8 space-y-2">
                          {solution.features.map((f) => (
                            <li key={f} className="flex items-center gap-3 text-base text-dark">
                              <img src={images.checkIcon2} alt="" className="w-5 h-5" />
                              {f}
                            </li>
                          ))}
                        </ul>
                        <a href="#" className={`mt-8 inline-flex items-center gap-2 ${solution.linkColor} text-base`}>
                          了解更多
                          <img src={images.arrowIcon} alt="" className="w-5 h-5" />
                        </a>
                      </div>
                      <img src={solution.image} alt={solution.title} className="w-[292px] h-[350px] object-contain" />
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
