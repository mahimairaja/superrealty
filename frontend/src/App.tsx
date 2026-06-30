import { BrowserRouter, Route, Routes } from "react-router-dom";
import Hub from "@/components/app/hub";
import Call from "@/routes/call";
import Onboard from "@/routes/onboard";
import Pipeline from "@/routes/pipeline";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Hub />} />
        <Route path="/call" element={<Call />} />
        <Route path="/onboard" element={<Onboard />} />
        <Route path="/pipeline" element={<Pipeline />} />
      </Routes>
    </BrowserRouter>
  );
}
