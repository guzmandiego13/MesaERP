import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import Login from "@/pages/Login";
import CompanySelector from "@/pages/CompanySelector";
import Dashboard from "@/pages/Dashboard";
import Finance from "@/pages/Finance";
import Sales from "@/pages/Sales";
import Inventory from "@/pages/Inventory";
import Procurement from "@/pages/Procurement";
import Settings from "@/pages/Settings";
import Layout from "@/components/Layout";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);

  useEffect(() => {
    if (token) {
      const userData = localStorage.getItem("user");
      const tenantData = localStorage.getItem("tenant");
      const companyData = localStorage.getItem("selectedCompany");
      if (userData) setUser(JSON.parse(userData));
      if (tenantData) setTenant(JSON.parse(tenantData));
      if (companyData) setSelectedCompany(JSON.parse(companyData));
    }
  }, [token]);

  const handleLogin = (authData) => {
    setToken(authData.token);
    setUser(authData.user);
    setTenant(authData.tenant);
    localStorage.setItem("token", authData.token);
    localStorage.setItem("user", JSON.stringify(authData.user));
    localStorage.setItem("tenant", JSON.stringify(authData.tenant));
    // Don't set company yet - user will select it next
  };

  const handleCompanySelect = (company) => {
    setSelectedCompany(company);
    localStorage.setItem("selectedCompany", JSON.stringify(company));
  };

  const handleChangeCompany = () => {
    setSelectedCompany(null);
    localStorage.removeItem("selectedCompany");
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setTenant(null);
    setSelectedCompany(null);
    localStorage.clear();
  };

  if (!token) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </BrowserRouter>
    );
  }

  // Show company selector if no company is selected
  if (!selectedCompany) {
    return (
      <BrowserRouter>
        <Routes>
          <Route path="*" element={<CompanySelector onCompanySelect={handleCompanySelect} />} />
        </Routes>
      </BrowserRouter>
    );
  }

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route 
            path="/" 
            element={
              <Layout 
                user={user} 
                tenant={tenant} 
                company={selectedCompany}
                onLogout={handleLogout}
                onChangeCompany={handleChangeCompany}
              />
            }
          >
            <Route index element={<Dashboard company={selectedCompany} />} />
            <Route path="finance" element={<Finance company={selectedCompany} />} />
            <Route path="sales" element={<Sales company={selectedCompany} />} />
            <Route path="inventory" element={<Inventory company={selectedCompany} />} />
            <Route path="procurement" element={<Procurement company={selectedCompany} />} />
            <Route path="settings" element={<Settings company={selectedCompany} />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
