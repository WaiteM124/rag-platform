import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Skeleton } from "../ui/skeleton";
import { cn } from "../../lib/utils";

export type Collection = {
  id: string;
  label: string;
  enabled: boolean;
  status?: string;
  source_count?: number | null;
};

export function CollectionGrid() {
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

  return (
    <section className="home-collections" aria-labelledby="collections-heading">
      <div className="home-section-header">
        <h2 id="collections-heading" className="home-section-title">
          Collections
        </h2>
        <p className="home-section-lead">Pick a corpus to query with citations.</p>
      </div>
      <div className="home-collections-grid">
        {!collections &&
          [0, 1].map((i) => (
            <Card key={i} className="home-collection-card">
              <CardHeader>
                <Skeleton className="h-5 w-36" />
                <Skeleton className="h-4 w-full max-w-xs" />
              </CardHeader>
            </Card>
          ))}
        {collections?.map((c) => (
          <Card
            key={c.id}
            className={cn(
              "home-collection-card",
              c.enabled ? "home-collection-card--active" : "home-collection-card--soon",
            )}
          >
            <CardHeader className={cn("space-y-2", !c.enabled && "pb-6")}>
              <CardTitle
                className={cn(
                  "flex flex-wrap items-center gap-2 text-lg font-medium tracking-tight",
                  !c.enabled && "home-collection-soon-title",
                )}
              >
                {c.label}
                {!c.enabled && (
                  <Badge variant="outline" className="font-normal text-muted-foreground">
                    Coming soon
                  </Badge>
                )}
              </CardTitle>
              <CardDescription className={cn("text-sm leading-relaxed", !c.enabled && "text-muted-foreground/80")}>
                {c.enabled
                  ? `${c.source_count ?? "46"} verified public sources, licence-classified.`
                  : "Curated public tax guidance — releasing in a later phase."}
              </CardDescription>
            </CardHeader>
            {c.enabled && (
              <CardContent className="pt-0">
                <Button className="w-full sm:w-auto" onClick={() => navigate(`/chat/${c.id}`)}>
                  Open chat
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Button>
              </CardContent>
            )}
          </Card>
        ))}
      </div>
    </section>
  );
}