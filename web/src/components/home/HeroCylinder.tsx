import { useEffect, useRef } from "react";
import { useTheme } from "../../lib/theme";
import type { HeroTheme } from "./cylinder/themePalette";

export function HeroCylinder() {
  const rootRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    let cleanup: (() => void) | undefined;
    let cancelled = false;

    void import("./cylinder/mountHero").then((mod) => {
      if (cancelled || !rootRef.current) return;
      cleanup = mod.mountHero(rootRef.current, theme as HeroTheme);
    });

    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [theme]);

  return (
    <div
      ref={rootRef}
      className="hero-cylinder-root"
      role="presentation"
      aria-hidden="true"
      data-theme={theme}
    />
  );
}