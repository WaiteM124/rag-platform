export default function About() {
  return (
    <article className="about">
      <h1>About this demo</h1>
      <p>
        Production-style RAG over verified open sources: hybrid Postgres FTS + pgvector, reciprocal
        rank fusion, and Amazon Bedrock answers with licence-aware citations.
      </p>
      <h2>Architecture</h2>
      <pre className="diagram">{`Internet → ALB → ECS Fargate (FastAPI + React)
                ↓
         RDS Postgres + pgvector
                ↓
         Bedrock (embed + generate)`}</pre>
      <h2>Licence-aware retrieval</h2>
      <p>
        Class A/B sources may appear in full with attribution. Class C sources ground the model but
        responses cap verbatim overlap and always link to the canonical source.
      </p>
      <h2>Eval gates</h2>
      <p>
        pgvector integration tests run on every CI build; Bedrock-backed evals gate releases when model
        access is enabled.
      </p>
      <p>
        More work: <a href="https://ai.mileswaite.net">ai.mileswaite.net</a> · Code:{" "}
        <a href="https://github.com/WaiteM124/rag-platform">GitHub</a>
      </p>
    </article>
  );
}