import { motion } from "framer-motion";
import { ArrowRight, Lock, Shield, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { EXAMPLE_QUESTIONS } from "../data/examples";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Skeleton } from "../components/ui/skeleton";

type Collection = {
  id: string;
  label: string;
  enabled: boolean;
  status?: string;
  source_count?: number | null;
};

export default function Home() {
  const navigate = useNavigate();
  const [collections, setCollections] = useState<Collection[] | null>(null);

  useEffect(() => {
    fetch("/api/collections")
      .then((r) => r.json())
      .then((d) => setCollections(d.collections ?? []))
      .catch(() =>
        setCollections([
          { id: "complex-systems", label: "Complex Systems", enabled: true },
          { id: "uk-tax", label: "UK Tax", enabled: false, status: "coming_soon" },
        ]),
      );
  }, []);

  const reducedMotion =
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  return (
    <div className="space-y-12">
      <motion.section
        initial={reducedMotion ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="space-y-6 text-center"
      >
        <Badge variant="secondary" className="mx-auto">
          Production RAG demo · eu-west-2
        </Badge>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl md:text-5xl">
          Licence-aware retrieval with eval-gated releases
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Hybrid pgvector + full-text search, Bedrock answers with citations, and infrastructure you can
          inspect on GitHub.
        </p>
        <div className="flex flex-wrap justify-center gap-3 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <Shield className="h-4 w-4 text-primary" /> Licence classes A/B/C
          </span>
          <span className="inline-flex items-center gap-1">
            <Sparkles className="h-4 w-4 text-primary" /> CI eval gates
          </span>
          <span className="inline-flex items-center gap-1">
            <Lock className="h-4 w-4 text-primary" /> No tracking scripts
          </span>
        </div>
      </motion.section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Choose a collection</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {!collections &&
            [0, 1].map((i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-4 w-full" />
                </CardHeader>
              </Card>
            ))}
          {collections?.map((c) => (
            <Card
              key={c.id}
              className={c.enabled ? "transition-shadow hover:shadow-soft" : "opacity-70"}
            >
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {c.label}
                  {!c.enabled && <Badge variant="outline">Coming soon</Badge>}
                </CardTitle>
                <CardDescription>
                  {c.enabled
                    ? `${c.source_count ?? "46"} verified public sources`
                    : "HMRC / GOV.UK guidance in a later phase"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {(EXAMPLE_QUESTIONS[c.id] ?? []).slice(0, 3).map((q) => (
                    <li key={q}>
                      {c.enabled ? (
                        <button
                          type="button"
                          className="text-left hover:text-primary focus-visible:ring-2 focus-visible:ring-ring rounded-md"
                          onClick={() => navigate(`/chat/${c.id}?q=${encodeURIComponent(q)}`)}
                        >
                          {q}
                        </button>
                      ) : (
                        <span>{q}</span>
                      )}
                    </li>
                  ))}
                </ul>
                <Button
                  className="w-full"
                  disabled={!c.enabled}
                  onClick={() => navigate(`/chat/${c.id}`)}
                >
                  Open chat <ArrowRight className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <p className="text-center text-sm text-muted-foreground">
        Also see{" "}
        <Link className="text-primary underline-offset-2 hover:underline" to="/about">
          architecture & eval approach
        </Link>
      </p>
    </div>
  );
}