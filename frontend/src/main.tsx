import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { FleetCompliancePage } from "./pages/FleetCompliancePage";
import { EnginesPage } from "./pages/EnginesPage";
import { EngineDetailPage } from "./pages/EngineDetailPage";
import { ServiceBulletinsPage } from "./pages/ServiceBulletinsPage";
import { ShopVisitsPage } from "./pages/ShopVisitsPage";
import "./styles.css";

function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">T</span>
          <span>Talon Engine Services</span>
          <span className="brand-sub">Fleet Compliance Portal</span>
        </div>
        <nav>
          <NavLink to="/fleet-compliance">Fleet Compliance</NavLink>
          <NavLink to="/engines">Engines</NavLink>
          <NavLink to="/service-bulletins">Service Bulletins</NavLink>
          <NavLink to="/shop-visits">Shop Visits</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Navigate to="/fleet-compliance" replace />} />
          <Route path="/fleet-compliance" element={<FleetCompliancePage />} />
          <Route path="/engines" element={<EnginesPage />} />
          <Route path="/engines/:id" element={<EngineDetailPage />} />
          <Route path="/service-bulletins" element={<ServiceBulletinsPage />} />
          <Route path="/shop-visits" element={<ShopVisitsPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
