import { Link, Route, Routes } from "react-router-dom";
import About from "./pages/About";
import Chat from "./pages/Chat";

export default function App() {
  return (
    <div className="layout">
      <header>
        <Link to="/" className="brand">
          RAG Platform
        </Link>
        <nav>
          <Link to="/">Ask</Link>
          <Link to="/about">About</Link>
          <a href="https://github.com/WaiteM124/rag-platform" target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
        <button type="button" className="theme" onClick={() => document.body.classList.toggle("light")}>
          Theme
        </button>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Chat />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </main>
    </div>
  );
}