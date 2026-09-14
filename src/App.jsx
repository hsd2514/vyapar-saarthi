import { HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppProvider } from "./context/AppContext";
import Layout from "./components/Layout";
import Intake from "./pages/Intake";
import FeasibilityReport from "./pages/FeasibilityReport";
import FinancialPlan from "./pages/FinancialPlan";
import RepaymentPlan from "./pages/RepaymentPlan";
import Summary from "./pages/Summary";
import SharedSummaryView from "./pages/SharedSummaryView";
import Chaupal from "./pages/Chaupal";
import ChaupalThread from "./pages/ChaupalThread";
import ChaupalMod from "./pages/ChaupalMod";
import { ForumProvider } from "./context/ForumContext";
import SignInDialog from "./components/chaupal/SignInDialog";

export default function App() {
  return (
    <AppProvider>
      <ForumProvider>
      <HashRouter>
        <Routes>
          {/* Shared read-only view — rendered without the wizard sidebar Layout */}
          <Route path="/view/:id" element={<SharedSummaryView />} />

          {/* Main wizard — wrapped in the stepper Layout */}
          <Route
            path="/*"
            element={
              <Layout>
                <Routes>
                  <Route path="/" element={<Navigate to="/intake" replace />} />
                  <Route path="/intake" element={<Intake />} />
                  <Route path="/feasibility" element={<FeasibilityReport />} />
                  <Route path="/financial-plan" element={<FinancialPlan />} />
                  <Route path="/repayment-plan" element={<RepaymentPlan />} />
                  <Route path="/summary" element={<Summary />} />
                  {/* Vyapar Chaupal - the discussion forum. Reading is open; posting signs in by phone. */}
                  <Route path="/chaupal" element={<Chaupal />} />
                  <Route path="/chaupal/t/:id" element={<ChaupalThread />} />
                  <Route path="/chaupal/mod" element={<ChaupalMod />} />
                  <Route path="*" element={<Navigate to="/intake" replace />} />
                </Routes>
              </Layout>
            }
          />
        </Routes>
        <SignInDialog />
      </HashRouter>
      </ForumProvider>
    </AppProvider>
  );
}
