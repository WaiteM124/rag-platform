import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { type ReactNode } from "react";
import { useTheme } from "../lib/theme";
import { cn } from "../lib/utils";

export function MarkdownAnswer({
  text,
  streaming,
  onCitationClick,
}: {
  text: string;
  streaming?: boolean;
  onCitationClick?: (index: number) => void;
}) {
  const { theme } = useTheme();
  const processed = text.replace(/\[(\d+)\]/g, (_m, n) => `[${n}](#cite-${n})`);

  return (
    <div
      className={cn(
        "prose max-w-none",
        theme === "dark" ? "prose-invert" : "prose-slate",
        streaming && "typing-cursor",
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          a: ({ href, children }) => {
            const match = href?.match(/^#cite-(\d+)$/);
            if (match && onCitationClick) {
              const idx = Number(match[1]);
              return (
                <button
                  type="button"
                  className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-md bg-primary/20 px-1 text-xs font-semibold text-primary hover:bg-primary/30 focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => onCitationClick(idx)}
                >
                  {children}
                </button>
              );
            }
            return (
              <a href={href} className="text-primary underline-offset-2 hover:underline" target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
          p: ({ children }: { children?: ReactNode }) => (
            <p className="mb-3 leading-relaxed text-foreground/95">{children}</p>
          ),
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}