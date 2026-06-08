"use client";

import {
  useEffect,
  useState,
  type CSSProperties,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";

type FloatingPortalProps = {
  anchorRef: RefObject<HTMLElement | null>;
  open: boolean;
  children: ReactNode;
  placement?: "above" | "below";
  align?: "start" | "end";
  gap?: number;
};

export function FloatingPortal({
  anchorRef,
  open,
  children,
  placement = "below",
  align = "end",
  gap = 8,
}: FloatingPortalProps) {
  const [style, setStyle] = useState<CSSProperties>({ visibility: "hidden" });

  useEffect(() => {
    if (!open) return;

    const update = () => {
      const el = anchorRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const base: CSSProperties = {
        position: "fixed",
        zIndex: 9999,
        visibility: "visible",
      };

      if (placement === "below") {
        setStyle({
          ...base,
          top: rect.bottom + gap,
          ...(align === "end"
            ? { right: Math.max(8, window.innerWidth - rect.right) }
            : { left: Math.max(8, rect.left) }),
        });
      } else {
        setStyle({
          ...base,
          bottom: window.innerHeight - rect.top + gap,
          ...(align === "end"
            ? { right: Math.max(8, window.innerWidth - rect.right) }
            : { left: Math.max(8, rect.left) }),
        });
      }
    };

    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open, anchorRef, placement, align, gap]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(<div style={style}>{children}</div>, document.body);
}
