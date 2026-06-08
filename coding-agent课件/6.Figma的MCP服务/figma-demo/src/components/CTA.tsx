const supportCards = [
  {
    title: '技术支持团队',
    desc: '7x24小时技术支持，快速响应解决问题',
    contact: '400-888-8888',
    contactType: 'phone' as const,
  },
  {
    title: '专属客户经理',
    desc: '一对一服务，深度了解业务需求',
    contact: 'service@aicloud.com',
    contactType: 'email' as const,
  },
  {
    title: '定制化解决方案',
    desc: '根据行业特点，提供专属AI解决方案',
    contact: '立即咨询 →',
    contactType: 'link' as const,
  },
];

export default function CTA() {
  return (
    <section className="py-20 px-[60px]">
      <div className="max-w-[1440px] mx-auto text-center">
        <h2 className="text-[40px] font-medium text-dark leading-[52px]">
          双倍增长智能云，帮助企业实现云空间
        </h2>
        <p className="text-xl text-dark mt-4">
          立即开启您的AI智能之旅，专业团队为您提供一对一服务
        </p>

        <div className="mt-10 flex justify-center gap-6">
          <button className="px-10 py-4 bg-gradient-to-r from-primary via-primary-mid to-primary-dark text-white rounded-lg text-2xl hover:opacity-90 transition-opacity">
            免费试用→
          </button>
          <button className="px-10 py-4 border border-primary text-primary rounded-lg text-2xl hover:bg-primary/5 transition-colors">
            联系我们
          </button>
        </div>

        <div className="mt-16 grid grid-cols-3 gap-[27px]">
          {supportCards.map((card) => (
            <div
              key={card.title}
              className="bg-white/80 border-2 border-white rounded-2xl p-8 text-left hover:shadow-md transition-shadow"
            >
              <h3 className="text-2xl font-medium text-[#333]">{card.title}</h3>
              <p className="text-base text-[#333] mt-2">{card.desc}</p>
              <p className="text-base text-primary mt-4 flex items-center gap-2">
                {card.contactType === 'phone' && (
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2 3a1 1 0 011-1h2.153a1 1 0 01.986.836l.74 4.435a1 1 0 01-.54 1.06l-1.548.773a11.037 11.037 0 006.105 6.105l.774-1.548a1 1 0 011.059-.54l4.435.74a1 1 0 01.836.986V17a1 1 0 01-1 1h-2C7.82 18 2 12.18 2 5V3z" />
                  </svg>
                )}
                {card.contactType === 'email' && (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                    <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
                  </svg>
                )}
                {card.contact}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
