import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export default function About() {
  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight">About</h1>
      <Card>
        <CardHeader>
          <CardTitle>Architecture</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-muted-foreground">
          <pre className="rounded-2xl border border-border bg-muted p-4 text-xs text-foreground">
            {`Cloudflare → ALB → ECS Fargate (FastAPI + React)
                      ↓
            RDS Postgres 16 + pgvector
                      ↓
            Amazon Bedrock (embed + generate)`}
          </pre>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Licence-aware retrieval</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground leading-relaxed">
          Sources are classed A/B/C. Open licences allow fuller quoting; class C responses cap verbatim
          overlap and always link to the canonical URL.
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Eval approach</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground leading-relaxed">
          pgvector integration tests run on every CI build; Bedrock-backed evals gate releases when model
          access is enabled.
        </CardContent>
      </Card>
      <p className="text-sm text-muted-foreground">
        <a href="https://ai.mileswaite.net" className="text-primary hover:underline">
          ai.mileswaite.net
        </a>
        {" · "}
        <a
          href="https://github.com/WaiteM124/rag-platform"
          className="text-primary hover:underline"
        >
          GitHub
        </a>
      </p>
    </article>
  );
}