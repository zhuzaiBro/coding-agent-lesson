import { images } from '../assets/images';

const services = [
  {
    title: '机器学习',
    subtitle: '提供完整的机器学习平台',
    desc: '从模型训练到部署的一站式服务',
    image: images.serviceCard,
    decoration: images.cardDecorations.union1,
    iconImg: images.cardDecorations.ai,
    ellipse: images.cardDecorations.ellipse,
  },
  {
    title: '计算机视觉',
    subtitle: '图像识别与分析服务',
    desc: '人脸识别、物体检测等能力',
    image: images.serviceCard,
    decoration: images.cardDecorations.union2,
    iconImg: images.cardDecorations.face,
    ellipse: images.cardDecorations.ellipse,
  },
  {
    title: '智能对话',
    subtitle: '先进的自然语言处理技术',
    desc: '打造智能客服与对话系统',
    image: images.serviceCard,
    decoration: images.cardDecorations.union3,
    iconImg: images.cardDecorations.data,
    ellipse: images.cardDecorations.ellipse,
  },
  {
    title: '数据智能',
    subtitle: '大数据分析与挖掘',
    desc: '助力企业数据驱动决策',
    image: images.serviceCard,
    decoration: images.cardDecorations.union4,
    iconImg: images.cardDecorations.model,
    ellipse: images.cardDecorations.ellipse,
  },
];

export default function Services() {
  return (
    <section className="py-20 px-[60px]">
      <div className="max-w-[1440px] mx-auto">
        <h2 className="text-[40px] font-medium text-dark text-center leading-[52px]">
          一站式AI企业服务体验
        </h2>
        <p className="text-xl text-dark text-center mt-4">
          为企业提供全方位的人工智能解决方案
        </p>

        <div className="mt-16 grid grid-cols-4 gap-[25px]">
          {services.map((service) => (
            <div
              key={service.title}
              className="bg-white rounded-2xl p-10 pb-0 overflow-hidden hover:shadow-lg transition-shadow group relative"
            >
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-[32px] font-medium text-dark leading-[52px]">
                  {service.title}
                </h3>
                <div className="relative w-10 h-10">
                  <img src={service.ellipse} alt="" className="w-10 h-10 opacity-60 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
              <p className="text-xl text-dark">{service.subtitle}</p>
              <p className="text-sm text-gray-light mt-1">{service.desc}</p>
              <div className="mt-8 flex justify-center relative h-[210px]">
                <img
                  src={service.image}
                  alt={service.title}
                  className="w-[215px] h-[202px] object-cover group-hover:scale-105 transition-transform"
                />
                <img
                  src={service.decoration}
                  alt=""
                  className="absolute -left-4 top-0 w-12 h-14 opacity-50"
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
