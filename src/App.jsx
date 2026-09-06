import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import Layout from "./components/Layout";
import Intake from "./pages/Intake";
import Calculators from "./pages/Calculators";
import Viability from "./pages/Viability";
import Schemes from "./pages/Schemes";
import Summary from "./pages/Summary";

export default function App() {
  return (
    <AppProvider>
      <HashRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/intake" replace />} />
            <Route path="/intake" element={<Intake />} />
            <Route path="/calculators" element={<Calculators />} />
            <Route path="/viability" element={<Viability />} />
            <Route path="/schemes" element={<Schemes />} />
            <Route path="/summary" element={<Summary />} />
            <Route path="*" element={<Navigate to="/intake" replace />} />
          </Routes>
        </Layout>
      </HashRouter>
    </AppProvider>
  );
}
