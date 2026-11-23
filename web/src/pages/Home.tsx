import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import { CollectionGrid } from "../components/home/CollectionGrid";
import { HeroCylinderLazy } from "../components/home/HeroCylinderLazy";
import { HowItWorks } from "../components/home/HowItWorks";
import "../home.css";

export default function Home() {
  return (
    <div className="home">
      <section className="home-hero" aria-labelledby="home-headline">
        <div className="home-hero-copy">
          <p className="home-eyebrow">Production RAG demo</p>
          <h1 id="home-headline" className="home-headline">
            Ask the research. Get cited answers.
          </h1>
          <p className="home-subline">
            <span className="home-subline-part">Licence-aware retrieval</span>
            <span className="home-subline-part">Eval-gated releases</span>
            <span className="home-subline-part">Open models on AWS</span>
          </p>
          <div className="home-hero-cta">
            <Button asChild size="lg" className="rounded-full px-6">
              <Link to="/chat/complex-systems">
                Start in Chat
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </div>
        <div className="home-hero-visual">
          <HeroCylinderLazy />
        </div>
      </section>

      <CollectionGrid />
      <HowItWorks />
    </div>
  );
}