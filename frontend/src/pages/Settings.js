import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Plus, Building2, Briefcase } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Settings({ company }) {
  const [subsidiaries, setSubsidiaries] = useState([]);
  const [businessUnits, setBusinessUnits] = useState([]);
  const [users, setUsers] = useState([]);
  const [apiKeys, setAPIKeys] = useState([]);
  const [branding, setBranding] = useState(null);
  
  const [showCompanyDialog, setShowCompanyDialog] = useState(false);
  const [showBUDialog, setShowBUDialog] = useState(false);
  const [showUserDialog, setShowUserDialog] = useState(false);
  const [showAPIDialog, setShowAPIDialog] = useState(false);

  const [companyForm, setCompanyForm] = useState({
    name: "",
    industry: "restaurant",
    tax_id: "",
    accounting_basis: "Accrual"
  });

  const [buForm, setBUForm] = useState({
    name: "",
    code: "",
    description: "",
    manager_name: ""
  });
  
  const [userForm, setUserForm] = useState({
    email: "",
    password: "",
    name: "",
    role: "Analyst",
    permissions: {
      view_dashboard: true,
      manage_information: false,
      manage_accounts_ledger: false,
      full_access: false
    }
  });
  
  const [apiForm, setAPIForm] = useState({
    name: "",
    service_type: "parrot_pos",
    api_key: "",
    api_secret: ""
  });
  
  const [brandingForm, setBrandingForm] = useState({
    logo_url: "",
    primary_color: "#3b82f6",
    secondary_color: "#8b5cf6",
    accent_color: "#10b981"
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [companiesRes, buRes, usersRes, apiKeysRes, brandingRes] = await Promise.all([
        axios.get(`${API}/companies`, { headers }),
        axios.get(`${API}/business-units?company_id=${company.id}`, { headers }),
        axios.get(`${API}/users`, { headers }),
        axios.get(`${API}/api-keys/${company.id}`, { headers }),
        axios.get(`${API}/branding/${company.id}`, { headers })
      ]);
      
      // Filter subsidiaries of current company
      const subs = companiesRes.data.filter(c => c.parent_company_id === company.id);
      setSubsidiaries(subs);
      setBusinessUnits(buRes.data);
      setUsers(usersRes.data);
      setAPIKeys(apiKeysRes.data);
      setBranding(brandingRes.data);
      setBrandingForm({
        logo_url: brandingRes.data.logo_url || "",
        primary_color: brandingRes.data.primary_color || "#3b82f6",
        secondary_color: brandingRes.data.secondary_color || "#8b5cf6",
        accent_color: brandingRes.data.accent_color || "#10b981"
      });
    } catch (error) {
      toast.error("Failed to load data");
    }
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/companies`, {
        ...companyForm,
        parent_company_id: company.id  // Always create as subsidiary of current parent
      }, { headers });
      toast.success("Subsidiary company created successfully");
      setShowCompanyDialog(false);
      setCompanyForm({
        name: "",
        industry: "restaurant",
        tax_id: "",
        accounting_basis: "Accrual"
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create subsidiary");
    }
  };

  const handleCreateBU = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/business-units`, {
        ...buForm,
        company_id: company.id  // Always create within current company
      }, { headers });
      toast.success("Business unit created successfully");
      setShowBUDialog(false);
      setBUForm({
        name: "",
        code: "",
        description: "",
        manager_name: ""
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create business unit");
    }
  };
  
  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/users`, userForm, { headers });
      toast.success("User created successfully");
      setShowUserDialog(false);
      setUserForm({
        email: "",
        password: "",
        name: "",
        role: "Analyst",
        permissions: {
          view_dashboard: true,
          manage_information: false,
          manage_accounts_ledger: false,
          full_access: false
        }
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create user");
    }
  };
  
  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Are you sure you want to delete this user?")) return;
    
    try {
      await axios.delete(`${API}/users/${userId}`, { headers });
      toast.success("User deleted");
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete user");
    }
  };
  
  const handleCreateAPIKey = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/api-keys/${company.id}`, apiForm, { headers });
      toast.success("API key added successfully");
      setShowAPIDialog(false);
      setAPIForm({
        name: "",
        service_type: "parrot_pos",
        api_key: "",
        api_secret: ""
      });
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to add API key");
    }
  };
  
  const handleDeleteAPIKey = async (keyId) => {
    if (!window.confirm("Are you sure you want to delete this API key?")) return;
    
    try {
      await axios.delete(`${API}/api-keys/${keyId}`, { headers });
      toast.success("API key deleted");
      loadData();
    } catch (error) {
      toast.error("Failed to delete API key");
    }
  };
  
  const handleUpdateBranding = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.put(`${API}/branding/${company.id}`, brandingForm, { headers });
      setBranding(response.data);
      toast.success("Branding updated successfully");
      // Reload to apply new branding
      window.location.reload();
    } catch (error) {
      toast.error("Failed to update branding");
    }
  };

  return (
    <div className="p-8 space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-600 mt-1">Manage subsidiaries and business units for {company.name}</p>
      </div>

      <Tabs defaultValue="subsidiaries" className="w-full">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="subsidiaries">Subsidiaries</TabsTrigger>
          <TabsTrigger value="business-units">Business Units</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="apis">APIs</TabsTrigger>
          <TabsTrigger value="branding">Branding</TabsTrigger>
        </TabsList>

        <TabsContent value="subsidiaries">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Subsidiary Companies</CardTitle>
              <Dialog open={showCompanyDialog} onOpenChange={setShowCompanyDialog}>
                <DialogTrigger asChild>
                  <Button data-testid="create-subsidiary">
                    <Plus className="w-4 h-4 mr-2" />
                    New Subsidiary
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Subsidiary Company</DialogTitle>
                    <DialogDescription>
                      Add a subsidiary company under {company.name}
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleCreateCompany} className="space-y-4">
                    <div>
                      <Label>Company Name *</Label>
                      <Input
                        value={companyForm.name}
                        onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                        placeholder="Acme Corp"
                        required
                      />
                    </div>
                    <div>
                      <Label>Industry *</Label>
                      <select
                        value={companyForm.industry}
                        onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        required
                      >
                        <option value="restaurant">Restaurant</option>
                        <option value="retail">Retail</option>
                      </select>
                    </div>
                    <div className="p-3 bg-blue-50 rounded-md">
                      <p className="text-sm text-blue-900">
                        <strong>Parent Company:</strong> {company.name}
                      </p>
                      <p className="text-xs text-blue-700 mt-1">
                        This subsidiary will be created under the current parent company
                      </p>
                    </div>
                    <div>
                      <Label>Tax ID</Label>
                      <Input
                        value={companyForm.tax_id}
                        onChange={(e) => setCompanyForm({ ...companyForm, tax_id: e.target.value })}
                        placeholder="XX-XXXXXXX"
                      />
                    </div>
                    <div>
                      <Label>Accounting Basis</Label>
                      <select
                        value={companyForm.accounting_basis}
                        onChange={(e) => setCompanyForm({ ...companyForm, accounting_basis: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="Accrual">Accrual</option>
                        <option value="Cash">Cash</option>
                      </select>
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" onClick={() => setShowCompanyDialog(false)}>
                        Cancel
                      </Button>
                      <Button type="submit">Create Subsidiary</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {subsidiaries.length > 0 ? (
                <div className="space-y-3">
                  {subsidiaries.map((sub) => (
                    <div key={sub.id} className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">
                      <div className="flex items-center gap-3">
                        <Building2 className="w-8 h-8 text-indigo-600" />
                        <div>
                          <h3 className="font-semibold text-slate-900">{sub.name}</h3>
                          <p className="text-sm text-slate-600 capitalize">{sub.industry}</p>
                          {sub.tax_id && (
                            <p className="text-xs text-slate-500 mt-1">Tax ID: {sub.tax_id}</p>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                          Subsidiary
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">No subsidiary companies yet</p>
                  <p className="text-sm text-slate-400 mt-2">Create subsidiaries under {company.name}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="business-units">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Business Units</CardTitle>
              <Dialog open={showBUDialog} onOpenChange={setShowBUDialog}>
                <DialogTrigger asChild>
                  <Button data-testid="create-business-unit">
                    <Plus className="w-4 h-4 mr-2" />
                    New Business Unit
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create Business Unit</DialogTitle>
                    <DialogDescription>
                      Add a new business unit to track revenues and expenses separately
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleCreateBU} className="space-y-4">
                    <div className="p-3 bg-blue-50 rounded-md">
                      <p className="text-sm text-blue-900">
                        <strong>Company:</strong> {company.name}
                      </p>
                      <p className="text-xs text-blue-700 mt-1">
                        This business unit will be created within the current company
                      </p>
                    </div>
                    <div>
                      <Label>Business Unit Name *</Label>
                      <Input
                        value={buForm.name}
                        onChange={(e) => setBUForm({ ...buForm, name: e.target.value })}
                        placeholder="Sales Department"
                        required
                      />
                    </div>
                    <div>
                      <Label>Code *</Label>
                      <Input
                        value={buForm.code}
                        onChange={(e) => setBUForm({ ...buForm, code: e.target.value })}
                        placeholder="BU-SALES"
                        required
                      />
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Input
                        value={buForm.description}
                        onChange={(e) => setBUForm({ ...buForm, description: e.target.value })}
                        placeholder="Handles all sales operations"
                      />
                    </div>
                    <div>
                      <Label>Manager Name</Label>
                      <Input
                        value={buForm.manager_name}
                        onChange={(e) => setBUForm({ ...buForm, manager_name: e.target.value })}
                        placeholder="John Doe"
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" onClick={() => setShowBUDialog(false)}>
                        Cancel
                      </Button>
                      <Button type="submit">Create Business Unit</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {businessUnits.length > 0 ? (
                <div className="space-y-3">
                  {businessUnits.map((bu) => (
                    <div
                      key={bu.id}
                      className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <Briefcase className="w-6 h-6 text-indigo-600" />
                        <div>
                          <h4 className="font-semibold text-slate-900">{bu.name}</h4>
                          <p className="text-sm text-slate-600">
                            {bu.company_name} • Code: {bu.code}
                          </p>
                          {bu.description && (
                            <p className="text-xs text-slate-500 mt-1">{bu.description}</p>
                          )}
                        </div>
                      </div>
                      {bu.manager_name && (
                        <div className="text-right">
                          <p className="text-xs font-medium text-slate-600">Manager</p>
                          <p className="text-sm text-slate-900">{bu.manager_name}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">No business units yet</p>
                  <p className="text-sm text-slate-400 mt-2">Create business units to track financials separately</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
