import { Github, Moon, Sun } from "lucide-react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { useTheme } from "../lib/theme";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";

export function Shell() {
  const { theme, toggle } = useTheme();
  const { pathname } = useLocation();
  const isHome = pathname === "/";

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b border-border/80 bg-background/90 backdrop-blur-md">
        <div
          className={cn(
            "mx-auto flex h-14 min-w-0 items-center justify-between gap-2 px-3 sm:gap-4 sm:px-6",
            isHome ? "max-w-7xl" : "max-w-6xl",
          )}
        >
          <Link
            to="/"
            className="shrink-0 rounded-lg px-0.5 font-semibold tracking-tight text-foreground focus-visible:ring-2 focus-visible:ring-ring sm:px-1"
          >
            <span className="whitespace-nowrap sm:hidden">
              <span aria-hidden="true">RAG</span>
              <span className="sr-only">RAG Platform</span>
            </span>
            <span className="hidden whitespace-nowrap sm:inline">RAG Platform</span>
          </Link>
          <nav className="flex shrink-0 items-center gap-0.5 text-sm sm:gap-1">
            <Link
              to="/"
              className="rounded-lg px-2 py-2 text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring sm:px-3"
            >
              Home
            </Link>
            <Link
              to="/chat/complex-systems"
              className="rounded-lg px-2 py-2 text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring sm:px-3"
            >
              Chat
            </Link>
            <Link
              to="/about"
              className="rounded-lg px-2 py-2 text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring sm:px-3"
            >
              About
            </Link>
            <a
              href="https://github.com/WaiteM124/rag-platform"
              className="rounded-lg p-2 text-muted-foreground hover:text-foreground hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="GitHub repository"
            >
              <Github className="h-4 w-4" />
            </a>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </nav>
        </div>
      </header>
      <main
        className={cn(
          "mx-auto px-4 sm:px-6",
          isHome ? "max-w-7xl py-10 md:py-14" : "max-w-6xl py-8",
        )}
      >
        <Outlet />
      </main>
    </div>
  );
}