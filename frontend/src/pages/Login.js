import { useState } from "react";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Login({ onLogin }) {
  const [isSetup, setIsSetup] = useState(false);
  const [loading, setLoading] = useState(false);

  const [loginData, setLoginData] = useState({ email: "", password: "" });
  const [setupData, setSetupData] = useState({
    name: "",
    industry: "restaurant",
    admin_email: "",
    admin_password: "",
    admin_name: ""
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, loginData);
      onLogin(response.data);
      toast.success("Logged in successfully!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/setup`, setupData);
      onLogin(response.data);
      toast.success("Tenant created successfully!");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Setup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">MesaERP</h1>
          <p className="text-slate-600">Multi-tenant ERP for Restaurants & Retail</p>
        </div>

        <Tabs defaultValue="login" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="login" data-testid="login-tab">Login</TabsTrigger>
            <TabsTrigger value="setup" data-testid="setup-tab">Setup New Tenant</TabsTrigger>
          </TabsList>

          <TabsContent value="login">
            <Card>
              <CardHeader>
                <CardTitle>Login</CardTitle>
                <CardDescription>Enter your credentials to access your account</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleLogin} className="space-y-4">
                  <div>
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      data-testid="login-email"
                      value={loginData.email}
                      onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      data-testid="login-password"
                      value={loginData.password}
                      onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={loading} data-testid="login-submit">
                    {loading ? "Logging in..." : "Login"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="setup">
            <Card>
              <CardHeader>
                <CardTitle>Setup New Tenant</CardTitle>
                <CardDescription>Create a new organization account</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSetup} className="space-y-4">
                  <div>
                    <Label htmlFor="tenant-name">Company Name</Label>
                    <Input
                      id="tenant-name"
                      data-testid="setup-company-name"
                      value={setupData.name}
                      onChange={(e) => setSetupData({ ...setupData, name: e.target.value })}
                      placeholder="My Restaurant Chain"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="industry">Industry</Label>
                    <select
                      id="industry"
                      data-testid="setup-industry"
                      value={setupData.industry}
                      onChange={(e) => setSetupData({ ...setupData, industry: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="restaurant">Restaurant</option>
                      <option value="retail">Retail</option>
                    </select>
                  </div>
                  <div>
                    <Label htmlFor="admin-name">Admin Name</Label>
                    <Input
                      id="admin-name"
                      data-testid="setup-admin-name"
                      value={setupData.admin_name}
                      onChange={(e) => setSetupData({ ...setupData, admin_name: e.target.value })}
                      placeholder="John Doe"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="admin-email">Admin Email</Label>
                    <Input
                      id="admin-email"
                      type="email"
                      data-testid="setup-admin-email"
                      value={setupData.admin_email}
                      onChange={(e) => setSetupData({ ...setupData, admin_email: e.target.value })}
                      placeholder="admin@company.com"
                      required
                    />
                  </div>
                  <div>
                    <Label htmlFor="admin-password">Admin Password</Label>
                    <Input
                      id="admin-password"
                      type="password"
                      data-testid="setup-admin-password"
                      value={setupData.admin_password}
                      onChange={(e) => setSetupData({ ...setupData, admin_password: e.target.value })}
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={loading} data-testid="setup-submit">
                    {loading ? "Creating..." : "Create Tenant"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
