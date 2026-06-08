"use client";

type LabLoadingProps = {
  /** sm: 上传按钮等小场景；md: 预览区；lg: 全屏 overlay */
  size?: "sm" | "md" | "lg";
  message?: string;
  className?: string;
};

const sizeMap = {
  sm: { img: 28, text: "text-xs" },
  md: { img: 120, text: "text-sm" },
  lg: { img: 200, text: "text-base" },
} as const;

export function LabLoading({
  size = "md",
  message,
  className = "",
}: LabLoadingProps) {
  const { img, text } = sizeMap[size];

  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 ${className}`}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/loading.gif"
        alt=""
        width={img}
        height={img}
        className="object-contain drop-shadow-md"
        draggable={false}
      />
      {message && (
        <p className={`${text} font-medium text-[var(--lab-text-muted)]`}>
          {message}
        </p>
      )}
    </div>
  );
}
