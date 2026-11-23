import { ExternalLink } from "lucide-react";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

export type Citation = {
  index: number;
  title: string;
  url: string;
  licence_class: string;
  mode: string;
  attribution?: string;
};

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) {
    return (
      <p className="text-sm text-muted-foreground">Citations appear when the model references sources.</p>
    );
  }
  return (
    <ul className="space-y-3">
      {citations.map((c) => (
        <li key={c.index}>
          <Card className="shadow-none">
            <CardHeader className="p-4 pb-2">
              <div className="flex items-start justify-between gap-2">
                <CardTitle className="text-sm font-medium">
                  [{c.index}] {c.title}
                </CardTitle>
                <Badge variant={c.mode === "excerpt_link" ? "excerpt" : "licence"}>
                  {c.mode === "excerpt_link" ? "Excerpt + link" : `Class ${c.licence_class}`}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <a
                href={c.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm text-primary hover:underline focus-visible:ring-2 focus-visible:ring-ring"
              >
                View source <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </CardContent>
          </Card>
        </li>
      ))}
    </ul>
  );
}