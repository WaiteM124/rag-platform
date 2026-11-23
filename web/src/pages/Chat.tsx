import { FormEvent, useEffect, useState } from "react";

type Collection = { id: string; label: string; enabled: boolean; status?: string };
type Citation = {
  index: number;
  title: string;
  url: string;
  licence_class: string;
  mode: string;
};

export default function Chat() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [collection, setCollection] = useState("complex-systems");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [meta, setMeta] = useState<{ latency_ms?: number; cost_gbp?: number }>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/collections")
      .then((r) => r.json())
      .then((d) => setCollections(d.collections ?? []))
      .catch(() => setCollections([{ id: "complex-systems", label: "Complex Systems", enabled: true }]));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setAnswer("");
    setCitations([]);
    setMeta({});
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collection, question }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error("no stream");
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const payload = JSON.parse(part.slice(6));
          if (payload.type === "delta") setAnswer((a) => a + payload.text);
          if (payload.type === "done") {
            setAnswer(payload.answer ?? "");
            setCitations(payload.citations ?? []);
            setMeta({ latency_ms: payload.latency_ms, cost_gbp: payload.cost_gbp });
          }
          if (payload.type === "error") setError(payload.message);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat">
      <h1>Ask the corpus</h1>
      <label>
        Collection
        <select value={collection} onChange={(e) => setCollection(e.target.value)}>
          {collections.map((c) => (
            <option key={c.id} value={c.id} disabled={!c.enabled}>
              {c.label}
              {c.status === "coming_soon" ? " (coming soon)" : ""}
            </option>
          ))}
        </select>
      </label>
      <form onSubmit={onSubmit}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          maxLength={1000}
          rows={4}
          placeholder="Your question…"
          required
        />
        <button type="submit" disabled={loading || collection !== "complex-systems"}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {answer && (
        <section className="answer">
          <h2>Answer</h2>
          <pre>{answer}</pre>
          <div className="meta">
            {meta.latency_ms != null && <span>{meta.latency_ms} ms</span>}
            {meta.cost_gbp != null && <span>£{meta.cost_gbp.toFixed(4)} est.</span>}
          </div>
          <h3>Citations</h3>
          <ul className="citations">
            {citations.map((c) => (
              <li key={c.index}>
                <strong>[{c.index}]</strong> {c.title} — class {c.licence_class} (
                {c.mode === "excerpt_link" ? "excerpt + link" : "full text"})
                <a href={c.url} target="_blank" rel="noreferrer">
                  Source
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}