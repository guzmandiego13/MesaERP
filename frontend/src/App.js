import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import axios from "axios";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Finance from "@/pages/Finance";
import Sales from "@/pages/Sales";
import Inventory from "@/pages/Inventory";
import Procurement from "@/pages/Procurement";
import Layout from "@/components/Layout";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);

  useEffect(() => {
    if (token) {
      const userData = localStorage.getItem("user");
      const tenantData = localStorage.getItem("tenant");
      if (userData) setUser(JSON.parse(userData));
      if (tenantData) setTenant(JSON.parse(tenantData));
    }
  }, [token]);

  const handleLogin = (authData) => {
    setToken(authData.token);
    setUser(authData.user);
    setTenant(authData.tenant);
    localStorage.setItem("token", authData.token);
    localStorage.setItem("user", JSON.stringify(authData.user));
    localStorage.setItem("tenant", JSON.stringify(authData.tenant));
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setTenant(null);
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

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout user={user} tenant={tenant} onLogout={handleLogout} />}>
            <Route index element={<Dashboard />} />
            <Route path="finance" element={<Finance />} />
            <Route path="sales" element={<Sales />} />
            <Route path="inventory" element={<Inventory />} />
            <Route path="procurement" element={<Procurement />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
