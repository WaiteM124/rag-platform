export type HeroTheme = "dark" | "light";

const LIGHT_STROKE: Record<number, string> = {
  0xff0000: "#b91c1c",
  0x00ff00: "#15803d",
  0xffffff: "#52525b",
};

const DARK_STROKE: Record<number, string> = {
  0xff0000: "#f87171",
  0x00ff00: "#4ade80",
  0xffffff: "#e4e4e7",
};

export function sceneBackground(theme: HeroTheme): number {
  return theme === "light" ? 0xfafafa : 0x101012;
}

export function strokeForArc(theme: HeroTheme, arcColor: number): string {
  const table = theme === "light" ? LIGHT_STROKE : DARK_STROKE;
  return table[arcColor] ?? `#${arcColor.toString(16).padStart(6, "0")}`;
}

export function lineColorForArc(theme: HeroTheme, arcColor: number): number {
  const hex = strokeForArc(theme, arcColor).replace("#", "");
  return Number.parseInt(hex, 16);
}

export function fallbackBackground(theme: HeroTheme): string {
  return theme === "light" ? "#fafafa" : "#101012";
}