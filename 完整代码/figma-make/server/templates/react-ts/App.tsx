// @ts-nocheck
import { Upload, FlaskConical } from "lucide-react";

export default function App() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-[#f4ffe8] via-[#fafff5] to-[#fff5eb] p-4">
      <div className="w-full max-w-xl space-y-8 text-center">
        <div className="space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-[#a2ff00] to-[#7acc00] text-gray-900 shadow-lg shadow-[#a2ff00]/25 ring-1 ring-[#7acc00]/30">
            <FlaskConical size={32} strokeWidth={2.2} />
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl">
            开始你的
            <span className="text-[#7acc00]">创作</span>
          </h1>
          <p className="text-lg text-[#5a6b4a]">
            在聊天框输入你的想法，或者上传文件，让创意落地。
          </p>
        </div>

        <div className="overflow-hidden rounded-2xl bg-white p-8 shadow-xl ring-1 ring-[#d4e8b8]/80">
          <div className="flex flex-col items-center justify-center space-y-6">
            <div className="rounded-full bg-[#f4ffe8] p-4 ring-1 ring-[#a2ff00]/20">
              <Upload className="h-8 w-8 text-[#7acc00]" />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-semibold text-gray-900">
                上传参考图或文档
              </h3>
              <p className="text-sm text-[#5a6b4a]">
                支持拖拽上传，或点击下方按钮选择文件
              </p>
            </div>
            <button className="inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-[#a2ff00] to-[#7acc00] px-6 py-3 text-sm font-semibold text-gray-900 shadow-sm transition-all hover:from-[#b8ff33] hover:to-[#8adb00] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#7acc00] active:scale-95">
              选择文件
            </button>
          </div>
        </div>

        <p className="text-sm text-[#5a6b4a]/70">
          Powered by{" "}
          <span className="font-medium text-[#ff8a00]">Zood Figma Make</span>
        </p>
      </div>
    </div>
  );
}
