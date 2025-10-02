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
  const [showCompanyDialog, setShowCompanyDialog] = useState(false);
  const [showBUDialog, setShowBUDialog] = useState(false);

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

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [companiesRes, buRes] = await Promise.all([
        axios.get(`${API}/companies`, { headers }),
        axios.get(`${API}/business-units?company_id=${company.id}`, { headers })
      ]);
      // Filter subsidiaries of current company
      const subs = companiesRes.data.filter(c => c.parent_company_id === company.id);
      setSubsidiaries(subs);
      setBusinessUnits(buRes.data);
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
      await axios.post(`${API}/business-units`, buForm, { headers });
      toast.success("Business unit created successfully");
      setShowBUDialog(false);
      setBUForm({
        company_id: "",
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

  const parentCompanies = companies.filter(c => !c.parent_company_id);

  return (
    <div className="p-8 space-y-6" data-testid="settings-page">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
        <p className="text-slate-600 mt-1">Manage companies and business units</p>
      </div>

      <Tabs defaultValue="companies" className="w-full">
        <TabsList>
          <TabsTrigger value="companies">Companies</TabsTrigger>
          <TabsTrigger value="business-units">Business Units</TabsTrigger>
        </TabsList>

        <TabsContent value="companies">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Companies & Subsidiaries</CardTitle>
              <Dialog open={showCompanyDialog} onOpenChange={setShowCompanyDialog}>
                <DialogTrigger asChild>
                  <Button data-testid="create-company">
                    <Plus className="w-4 h-4 mr-2" />
                    New Company
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create New Company</DialogTitle>
                    <DialogDescription>
                      Add a standalone company or subsidiary
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
                    <div>
                      <Label>Parent Company (Optional)</Label>
                      <select
                        value={companyForm.parent_company_id}
                        onChange={(e) => setCompanyForm({ ...companyForm, parent_company_id: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="">None (Standalone Company)</option>
                        {parentCompanies.map((company) => (
                          <option key={company.id} value={company.id}>
                            {company.name}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-slate-500 mt-1">
                        Select to create as a subsidiary
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
                      <Button type="submit">Create Company</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {companies.length > 0 ? (
                <div className="space-y-4">
                  {/* Parent Companies */}
                  {parentCompanies.map((company) => (
                    <div key={company.id} className="border border-slate-200 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <Building2 className="w-8 h-8 text-blue-600" />
                          <div>
                            <h3 className="text-lg font-semibold text-slate-900">{company.name}</h3>
                            <p className="text-sm text-slate-600 capitalize">{company.industry}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-medium text-slate-600">
                            {company.subsidiary_count} Subsidiaries
                          </span>
                          {company.tax_id && (
                            <p className="text-xs text-slate-500 mt-1">Tax ID: {company.tax_id}</p>
                          )}
                        </div>
                      </div>

                      {/* Subsidiaries */}
                      {companies.filter(c => c.parent_company_id === company.id).length > 0 && (
                        <div className="ml-12 mt-3 space-y-2">
                          <p className="text-xs font-medium text-slate-600 uppercase">Subsidiaries:</p>
                          {companies
                            .filter(c => c.parent_company_id === company.id)
                            .map((sub) => (
                              <div key={sub.id} className="flex items-center gap-2 p-2 bg-slate-50 rounded">
                                <Building2 className="w-5 h-5 text-slate-400" />
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-slate-900">{sub.name}</p>
                                  <p className="text-xs text-slate-500 capitalize">{sub.industry}</p>
                                </div>
                              </div>
                            ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <p className="text-slate-500">No companies yet</p>
                  <p className="text-sm text-slate-400 mt-2">Create your first company to get started</p>
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
                    <div>
                      <Label>Company *</Label>
                      <select
                        value={buForm.company_id}
                        onChange={(e) => setBUForm({ ...buForm, company_id: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        required
                      >
                        <option value="">Select Company</option>
                        {companies.map((company) => (
                          <option key={company.id} value={company.id}>
                            {company.name}
                          </option>
                        ))}
                      </select>
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
