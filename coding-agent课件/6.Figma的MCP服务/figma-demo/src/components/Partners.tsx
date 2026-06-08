import { images } from '../assets/images';

export default function Partners() {
  return (
    <section className="relative py-20 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent to-[#287be6]" />
      <img
        src={images.ctaBg}
        alt=""
        className="absolute inset-0 w-full h-full object-cover mix-blend-overlay"
      />

      <div className="relative z-10 max-w-[1440px] mx-auto px-[60px]">
        <h2 className="text-[40px] font-medium text-dark text-center leading-[52px]">
          与各行业伙伴，共创AI新价值
        </h2>
        <p className="text-xl text-dark text-center mt-4">
          超过10000+企业正在使用我们的服务
        </p>

        <div className="mt-12 space-y-5 overflow-hidden">
          <div className="flex animate-scroll-left" style={{ width: '200%' }}>
            {[...images.partnerLogos.row1, ...images.partnerLogos.row1].map((logo, i) => (
              <div
                key={i}
                className="flex-shrink-0 w-[224px] h-[80px] bg-white rounded-2xl flex items-center justify-center mx-2.5"
              >
                <img src={logo} alt="Partner" className="max-w-[160px] max-h-[52px] object-contain" />
              </div>
            ))}
          </div>

          <div className="flex animate-scroll-left" style={{ width: '200%', animationDirection: 'reverse', animationDuration: '35s' }}>
            {[...images.partnerLogos.row2, ...images.partnerLogos.row2].map((logo, i) => (
              <div
                key={i}
                className="flex-shrink-0 w-[224px] h-[80px] bg-white rounded-2xl flex items-center justify-center mx-2.5"
              >
                <img src={logo} alt="Partner" className="max-w-[160px] max-h-[52px] object-contain" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
