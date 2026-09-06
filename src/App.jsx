import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import Layout from "./components/Layout";
import Intake from "./pages/Intake";
import FeasibilityReport from "./pages/FeasibilityReport";
import FinancialPlan from "./pages/FinancialPlan";
import RepaymentPlan from "./pages/RepaymentPlan";
import Summary from "./pages/Summary";

export default function App() {
  return (
    <AppProvider>
      <HashRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Navigate to="/intake" replace />} />
            <Route path="/intake" element={<Intake />} />
            <Route path="/feasibility" element={<FeasibilityReport />} />
            <Route path="/financial-plan" element={<FinancialPlan />} />
            <Route path="/repayment-plan" element={<RepaymentPlan />} />
            <Route path="/summary" element={<Summary />} />
            <Route path="*" element={<Navigate to="/intake" replace />} />
          </Routes>
        </Layout>
      </HashRouter>
    </AppProvider>
  );
}
