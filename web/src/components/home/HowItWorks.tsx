const STEPS = [
  {
    title: "Retrieve",
    body: "Hybrid vector and full-text search over verified, licence-tagged sources.",
  },
  {
    title: "Answer",
    body: "Open models on AWS return grounded replies with inline citations.",
  },
  {
    title: "Release",
    body: "Eval suites must pass in CI before a collection ships to production.",
  },
] as const;

export function HowItWorks() {
  return (
    <section className="home-how" aria-labelledby="how-heading">
      <h2 id="how-heading" className="sr-only">
        How it works
      </h2>
      <ol className="home-how-list">
        {STEPS.map((step, index) => (
          <li key={step.title} className="home-how-item">
            <span className="home-how-index" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div className="space-y-1">
              <h3 className="text-sm font-medium tracking-tight text-foreground">{step.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}