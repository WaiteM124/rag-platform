import { lazy, Suspense } from "react";

const HeroCylinder = lazy(() =>
  import("./HeroCylinder").then((mod) => ({ default: mod.HeroCylinder })),
);

function HeroCylinderPlaceholder() {
  return (
    <div
      className="hero-cylinder-root hero-cylinder-root--placeholder"
      role="presentation"
      aria-hidden="true"
    />
  );
}

export function HeroCylinderLazy() {
  return (
    <Suspense fallback={<HeroCylinderPlaceholder />}>
      <HeroCylinder />
    </Suspense>
  );
}