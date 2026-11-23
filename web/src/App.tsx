import { Route, Routes } from "react-router-dom";
import { Shell } from "./components/Shell";
import About from "./pages/About";
import ChatPage from "./pages/Chat";
import Home from "./pages/Home";

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<Home />} />
        <Route path="/chat/:collectionId" element={<ChatPage />} />
        <Route path="/about" element={<About />} />
      </Route>
    </Routes>
  );
}