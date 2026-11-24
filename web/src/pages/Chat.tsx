import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { PanelRight, Send } from "lucide-react";
import { motion } from "framer-motion";
import { CitationList, type Citation } from "../components/CitationList";
import { MarkdownAnswer } from "../components/MarkdownAnswer";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Sheet } from "../components/ui/sheet";
import { Skeleton } from "../components/ui/skeleton";
import { Badge } from "../components/ui/badge";

export default function ChatPage() {
  const { collectionId = "complex-systems" } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [question, setQuestion] = useState(searchParams.get("q") ?? "");
  const [answer, setAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [meta, setMeta] = useState<{
    latency_ms?: number;
    cost_usd?: number | null;
    cost_status?: string;
    cost_gbp?: number | null;
    tokens?: { input: number; output: number };
  }>({});
  const [error, setError] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [highlight, setHighlight] = useState<number | null>(null);

  const collectionLabel = useMemo(
    () => (collectionId === "uk-tax" ? "UK Tax" : "Complex Systems"),
    [collectionId],
  );

  useEffect(() => {
    if (collectionId === "uk-tax") navigate("/");
  }, [collectionId, navigate]);

  const submit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      if (!question.trim() || collectionId !== "complex-systems") return;
      setStreaming(true);
      setError("");
      setAnswer("");
      setCitations([]);
      setMeta({});
      try {
        const res = await fetch("/api/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ collection: collectionId, question: question.trim() }),
        });
        if (!res.ok) throw new Error(await res.text());
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response stream");
        const decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const blocks = buffer.split("\n\n");
          buffer = blocks.pop() ?? "";
          for (const block of blocks) {
            const line = block.trim();
            if (!line.startsWith("data: ")) continue;
            const payload = JSON.parse(line.slice(6));
            if (payload.type === "delta") setAnswer((a) => a + payload.text);
            if (payload.type === "done") {
              setAnswer(payload.answer ?? "");
              setCitations(payload.citations ?? []);
              setMeta({
                latency_ms: payload.metrics?.total_ms ?? payload.latency_ms,
                cost_usd: payload.metrics?.cost_usd ?? payload.cost_usd,
                cost_status: payload.metrics?.cost_status ?? payload.cost_status,
                cost_gbp: payload.cost_gbp,
                tokens: payload.tokens,
              });
            }
            if (payload.type === "error") setError(payload.message);
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Request failed");
      } finally {
        setStreaming(false);
      }
    },
    [collectionId, question],
  );

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-2">
          <motion.h1 layout className="text-2xl font-semibold tracking-tight">
            {collectionLabel}
          </motion.h1>
          <Button
            variant="outline"
            size="sm"
            className="lg:hidden"
            onClick={() => setDrawerOpen(true)}
          >
            <PanelRight className="h-4 w-4" /> Citations
          </Button>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <label htmlFor="question" className="sr-only">
            Question
          </label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="Ask about complex systems, criticality, networks…"
            className="w-full resize-none rounded-2xl border border-input bg-card px-4 py-3 text-sm shadow-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="submit" disabled={streaming || !question.trim()}>
            <Send className="h-4 w-4" />
            {streaming ? "Streaming…" : "Ask"}
          </Button>
        </form>

        {error && (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-4 text-sm text-destructive">{error}</CardContent>
          </Card>
        )}

        {streaming && !answer && (
          <div className="space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        )}

        {!streaming && !answer && !error && (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              Ask a question to see streaming answers with numbered citations. Try an example from the
              home page.
            </CardContent>
          </Card>
        )}

        {answer && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Answer</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <MarkdownAnswer
                text={answer}
                streaming={streaming}
                onCitationClick={(idx) => {
                  setHighlight(idx);
                  setDrawerOpen(true);
                }}
              />
              {!streaming && (
                <footer className="flex flex-wrap gap-3 border-t border-border pt-4 text-xs text-muted-foreground">
                  <span className="font-mono text-[11px] tracking-tight">
                    {meta.latency_ms != null
                      ? `took ${Math.round(meta.latency_ms)} ms`
                      : "took — ms"}
                    {", "}
                    {meta.cost_status === "unverified" || meta.cost_usd == null
                      ? "~$unverified"
                      : `~$${Number(meta.cost_usd).toFixed(5)}`}
                  </span>
                  {meta.tokens && (
                    <Badge variant="outline">
                      {meta.tokens.input}+{meta.tokens.output} tokens
                    </Badge>
                  )}
                  {meta.cost_gbp != null && meta.cost_status !== "unverified" && (
                    <Badge variant="outline">£{meta.cost_gbp.toFixed(4)} est.</Badge>
                  )}
                </footer>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      <aside className="hidden lg:block">
        <Card className="sticky top-20 max-h-[calc(100vh-6rem)] overflow-y-auto">
          <CardHeader>
            <CardTitle className="text-base">Citations</CardTitle>
          </CardHeader>
          <CardContent>
            <CitationList citations={citations} />
          </CardContent>
        </Card>
      </aside>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen} title="Citations">
        <CitationList citations={highlight ? citations.filter((c) => c.index === highlight) : citations} />
      </Sheet>
    </div>
  );
}