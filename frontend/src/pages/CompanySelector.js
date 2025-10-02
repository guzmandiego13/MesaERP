import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Building2, Plus, ArrowRight, Users, Edit, Trash, RotateCcw, AlertTriangle } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function CompanySelector({ onCompanySelect }) {
  const [companies, setCompanies] = useState([]);
  const [deletedCompanies, setDeletedCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDeletedDialog, setShowDeletedDialog] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [companyToDelete, setCompanyToDelete] = useState(null);
  const [companyForm, setCompanyForm] = useState({
    name: "",
    industry: "restaurant",
    tax_id: "",
    accounting_basis: "Accrual"
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };
  const tenant = JSON.parse(localStorage.getItem("tenant") || "{}");

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      const [companiesRes, deletedRes] = await Promise.all([
        axios.get(`${API}/companies`, { headers }),
        axios.get(`${API}/companies/deleted`, { headers }).catch(() => ({ data: [] }))
      ]);
      
      // Filter to show only parent companies (no parent_company_id)
      const parentCompanies = companiesRes.data.filter(c => !c.parent_company_id);
      setCompanies(parentCompanies);
      
      // Filter deleted companies to only parent companies
      const deletedParentCompanies = deletedRes.data.filter(c => !c.parent_company_id);
      setDeletedCompanies(deletedParentCompanies);
    } catch (error) {
      toast.error("Failed to load companies");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API}/companies`, {
        ...companyForm,
        parent_company_id: null  // Always create as parent company
      }, { headers });
      
      toast.success("Parent company created successfully");
      setShowCreateDialog(false);
      setCompanyForm({
        name: "",
        industry: "restaurant",
        tax_id: "",
        accounting_basis: "Accrual"
      });
      
      // Auto-select the newly created company
      onCompanySelect(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create company");
    }
  };

  const handleEditCompany = (company) => {
    setEditingCompany(company.id);
    setCompanyForm({
      name: company.name,
      industry: company.industry,
      tax_id: company.tax_id || "",
      accounting_basis: company.accounting_basis
    });
  };

  const handleUpdateCompany = async (e) => {
    e.preventDefault();
    try {
      await axios.put(`${API}/companies/${editingCompany}`, companyForm, { headers });
      toast.success("Company updated successfully");
      setEditingCompany(null);
      loadCompanies();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update company");
    }
  };

  const handleDeleteClick = (company) => {
    setCompanyToDelete(company);
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = async () => {
    if (!companyToDelete) return;
    
    try {
      await axios.post(`${API}/companies/${companyToDelete.id}/soft-delete`, {}, { headers });
      toast.success(`Company "${companyToDelete.name}" has been deleted and backed up for 6 months`);
      setShowDeleteConfirm(false);
      setCompanyToDelete(null);
      loadCompanies();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete company");
    }
  };

  const handleRestoreCompany = async (companyId, companyName) => {
    if (!window.confirm(`Are you sure you want to restore "${companyName}"?`)) {
      return;
    }
    
    try {
      await axios.post(`${API}/companies/${companyId}/restore`, {}, { headers });
      toast.success(`Company "${companyName}" has been restored successfully`);
      loadCompanies();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to restore company");
    }
  };

  const cancelEdit = () => {
    setEditingCompany(null);
    setCompanyForm({
      name: "",
      industry: "restaurant", 
      tax_id: "",
      accounting_basis: "Accrual"
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
        <div className="text-slate-500">Loading companies...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 p-4">
      <div className="w-full max-w-4xl">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Select Company</h1>
          <p className="text-slate-600">Choose a company to work with or create a new one</p>
          <p className="text-sm text-slate-500 mt-2">Logged in as: {tenant.name}</p>
        </div>

        {/* Companies Grid */}
        {companies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {companies.map((company) => (
              <Card
                key={company.id}
                className="hover:shadow-lg transition-shadow border-2 hover:border-blue-400"
                data-testid={`select-company-${company.id}`}
              >
                {editingCompany === company.id ? (
                  // Edit Mode
                  <form onSubmit={handleUpdateCompany} className="p-6">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Building2 className="w-6 h-6 text-blue-600" />
                      </div>
                      <h3 className="text-lg font-semibold">Editing Company</h3>
                    </div>
                    
                    <div className="space-y-4">
                      <div>
                        <Label>Company Name</Label>
                        <Input
                          value={companyForm.name}
                          onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                          className="mt-1"
                          required
                        />
                      </div>
                      <div>
                        <Label>Industry</Label>
                        <select
                          value={companyForm.industry}
                          onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md mt-1"
                        >
                          <option value="restaurant">Restaurant</option>
                          <option value="retail">Retail</option>
                        </select>
                      </div>
                      <div>
                        <Label>Tax ID</Label>
                        <Input
                          value={companyForm.tax_id}
                          onChange={(e) => setCompanyForm({ ...companyForm, tax_id: e.target.value })}
                          className="mt-1"
                          placeholder="XX-XXXXXXX"
                        />
                      </div>
                      <div>
                        <Label>Accounting Basis</Label>
                        <select
                          value={companyForm.accounting_basis}
                          onChange={(e) => setCompanyForm({ ...companyForm, accounting_basis: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md mt-1"
                        >
                          <option value="Accrual">Accrual</option>
                          <option value="Cash">Cash</option>
                        </select>
                      </div>
                      
                      <div className="flex gap-2 pt-4">
                        <Button type="submit" className="flex-1">
                          Save Changes
                        </Button>
                        <Button type="button" variant="outline" onClick={cancelEdit} className="flex-1">
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </form>
                ) : (
                  // View Mode
                  <>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3" onClick={() => onCompanySelect(company)} className="cursor-pointer flex-1">
                          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                            <Building2 className="w-6 h-6 text-blue-600" />
                          </div>
                          <div>
                            <CardTitle className="text-xl">{company.name}</CardTitle>
                            <CardDescription className="capitalize mt-1">
                              {company.industry}
                            </CardDescription>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEditCompany(company);
                            }}
                            className="p-2 h-8 w-8"
                            title="Edit company"
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteClick(company);
                            }}
                            className="p-2 h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                            title="Delete company"
                          >
                            <Trash className="w-4 h-4" />
                          </Button>
                          <ArrowRight className="w-5 h-5 text-slate-400" />
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent onClick={() => onCompanySelect(company)} className="cursor-pointer">
                      <div className="space-y-2 text-sm">
                        {company.tax_id && (
                          <div className="flex justify-between">
                            <span className="text-slate-600">Tax ID:</span>
                            <span className="font-medium text-slate-900">{company.tax_id}</span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span className="text-slate-600">Accounting:</span>
                          <span className="font-medium text-slate-900">{company.accounting_basis}</span>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t">
                          <span className="text-slate-600 flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            Subsidiaries:
                          </span>
                          <span className="font-semibold text-blue-600">{company.subsidiary_count || 0}</span>
                        </div>
                      </div>
                    </CardContent>
                  </>
                )}
              </Card>
            ))}
          </div>
        ) : (
          <Card className="mb-6">
            <CardContent className="py-12 text-center">
              <Building2 className="w-16 h-16 text-slate-300 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">No Companies Yet</h3>
              <p className="text-slate-600 mb-6">Create your first parent company to get started</p>
            </CardContent>
          </Card>
        )}

        {/* Deleted Companies Button */}
        {deletedCompanies.length > 0 && (
          <div className="mb-4 text-center">
            <Button 
              variant="outline"
              onClick={() => setShowDeletedDialog(true)}
              className="text-orange-600 hover:text-orange-700"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              View Deleted Companies ({deletedCompanies.length})
            </Button>
          </div>
        )}

        {/* Create New Company Button */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button
              size="lg"
              className="w-full"
              data-testid="create-parent-company"
            >
              <Plus className="w-5 h-5 mr-2" />
              Create New Parent Company
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Parent Company</DialogTitle>
              <DialogDescription>
                Set up a new parent company. You can add subsidiaries and business units later.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateCompany} className="space-y-4">
              <div>
                <Label htmlFor="company-name">Company Name *</Label>
                <Input
                  id="company-name"
                  value={companyForm.name}
                  onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                  placeholder="Golden Food Group"
                  required
                  data-testid="company-name-input"
                />
              </div>
              <div>
                <Label htmlFor="industry">Industry *</Label>
                <select
                  id="industry"
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
                <Label htmlFor="tax-id">Tax ID</Label>
                <Input
                  id="tax-id"
                  value={companyForm.tax_id}
                  onChange={(e) => setCompanyForm({ ...companyForm, tax_id: e.target.value })}
                  placeholder="XX-XXXXXXX"
                />
              </div>
              <div>
                <Label htmlFor="accounting-basis">Accounting Basis</Label>
                <select
                  id="accounting-basis"
                  value={companyForm.accounting_basis}
                  onChange={(e) => setCompanyForm({ ...companyForm, accounting_basis: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="Accrual">Accrual</option>
                  <option value="Cash">Cash</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                  Cancel
                </Button>
                <Button type="submit" data-testid="submit-create-company">
                  Create Company
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Confirm Company Deletion
              </DialogTitle>
              <DialogDescription className="space-y-3 pt-2">
                <p className="font-medium text-slate-900">
                  Are you absolutely sure you want to delete "{companyToDelete?.name}"?
                </p>
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    <strong>This action will:</strong>
                  </p>
                  <ul className="text-xs text-yellow-700 mt-2 space-y-1 list-disc ml-4">
                    <li>Soft delete the company and all its data</li>
                    <li>Create a backup for 6 months</li>
                    <li>Allow restoration within 6 months</li>
                    <li>Permanently delete after 6 months</li>
                  </ul>
                </div>
                <p className="text-sm text-slate-600">
                  Type <strong>DELETE</strong> to confirm this action.
                </p>
                <Input
                  placeholder="Type DELETE to confirm"
                  onChange={(e) => {
                    const deleteButton = document.getElementById('confirm-delete-btn');
                    if (deleteButton) {
                      deleteButton.disabled = e.target.value !== 'DELETE';
                    }
                  }}
                  className="mt-2"
                />
              </DialogDescription>
            </DialogHeader>
            <div className="flex gap-2 pt-4">
              <Button 
                variant="outline" 
                onClick={() => {
                  setShowDeleteConfirm(false);
                  setCompanyToDelete(null);
                }}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button 
                id="confirm-delete-btn"
                onClick={handleConfirmDelete}
                className="flex-1 bg-red-600 hover:bg-red-700"
                disabled={true}
              >
                Delete Company
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Deleted Companies Dialog */}
        <Dialog open={showDeletedDialog} onOpenChange={setShowDeletedDialog}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <RotateCcw className="w-5 h-5 text-orange-600" />
                Deleted Companies
              </DialogTitle>
              <DialogDescription>
                Companies deleted within the last 6 months that can be restored
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {deletedCompanies.map((company) => (
                <div key={company.id} className="border border-orange-200 rounded-lg p-4 bg-orange-50">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                        <Building2 className="w-5 h-5 text-orange-600" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-900">{company.name}</h4>
                        <p className="text-sm text-slate-600 capitalize">{company.industry}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          Deleted: {new Date(company.deleted_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="mb-2">
                        <span className="text-xs font-medium text-slate-600">Days remaining:</span>
                        <div className={`text-sm font-bold ${
                          company.days_remaining > 30 ? 'text-green-600' : 
                          company.days_remaining > 7 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {company.days_remaining} days
                        </div>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleRestoreCompany(company.id, company.name)}
                        className="bg-green-600 hover:bg-green-700 text-white"
                      >
                        <RotateCcw className="w-4 h-4 mr-1" />
                        Restore
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
              
              {deletedCompanies.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-slate-500">No deleted companies available for restoration</p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
