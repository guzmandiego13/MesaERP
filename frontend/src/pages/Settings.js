import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Plus, Building2, Briefcase, Upload, Trash, Edit, Save, X, RotateCcw } from "lucide-react";

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
  const [showDeletedDialog, setShowDeletedDialog] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDeletedBUsDialog, setShowDeletedBUsDialog] = useState(false);
  const [deletedBusinessUnits, setDeletedBusinessUnits] = useState([]);

  // Remove CSV import state as it's moved to Finance page
  
  const [editingCompany, setEditingCompany] = useState(null);
  const [editingBU, setEditingBU] = useState(null);
  const [editingUser, setEditingUser] = useState(null);

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
    manager_name: "",
    parent_subsidiary_id: "",
    consolidation_enabled: true
  });
  
  const [userForm, setUserForm] = useState({
    email: "",
    password: "",
    name: "",
    role: "Analyst",
    permissions: {
      // Dashboard & Reporting
      view_dashboard: true,
      view_reports: false,
      export_data: false,
      
      // Financial Management
      view_finances: false,
      manage_accounts_ledger: false,
      create_journal_entries: false,
      approve_journal_entries: false,
      
      // Company & Business Units
      manage_information: false,
      manage_companies: false,
      manage_business_units: false,
      
      // User Management
      view_users: false,
      manage_users: false,
      
      // Settings & Configuration
      manage_settings: false,
      manage_api_keys: false,
      manage_branding: false,
      
      // Inventory & Operations
      view_inventory: false,
      manage_inventory: false,
      manage_procurement: false,
      
      // Administrative
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
    loadBankStatements();
  }, [company.id]);

  const loadData = async () => {
    try {
      const [companiesRes, buRes, usersRes, apiKeysRes, brandingRes, deletedBUsRes, accountsRes] = await Promise.all([
        axios.get(`${API}/companies`, { headers }),
        axios.get(`${API}/business-units?company_id=${company.id}`, { headers }),
        axios.get(`${API}/users`, { headers }),
        axios.get(`${API}/api-keys/${company.id}`, { headers }),
        axios.get(`${API}/branding/${company.id}`, { headers }),
        axios.get(`${API}/business-units/deleted`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${API}/accounts?company_id=${company.id}`, { headers }).catch(() => ({ data: [] }))
      ]);
      
      // Filter subsidiaries of current company
      const subs = companiesRes.data.filter(c => c.parent_company_id === company.id);
      setSubsidiaries(subs);
      setBusinessUnits(buRes.data);
      setUsers(usersRes.data);
      setAPIKeys(apiKeysRes.data);
      setBranding(brandingRes.data);
      setDeletedBusinessUnits(deletedBUsRes.data.filter(bu => bu.company_id === company.id));
      setAccounts(accountsRes.data);
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
        manager_name: "",
        parent_subsidiary_id: "",
        consolidation_enabled: true
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
  
  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    if (!['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)) {
      toast.error("Only JPG and PNG files are allowed");
      return;
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      toast.error("File size must be less than 5MB");
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(
        `${API}/upload-logo/${company.id}`,
        formData,
        {
          headers: {
            ...headers,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      setBrandingForm({ ...brandingForm, logo_url: response.data.logo_url });
      toast.success("Logo uploaded successfully");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload logo");
    }
  };

  const handleUpdateBranding = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.put(`${API}/branding/${company.id}`, brandingForm, { headers });
      setBranding(response.data);
      toast.success("Branding updated successfully");
      // Reload to apply new branding
      setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
      toast.error("Failed to update branding");
    }
  };

  // Helper function to render permission checkboxes
  const renderPermissionCheckbox = (key, label, description) => (
    <label key={key} className="flex items-start gap-3 p-3 border border-slate-200 rounded-lg hover:bg-slate-50">
      <input
        type="checkbox"
        checked={userForm.permissions[key]}
        onChange={(e) => setUserForm({
          ...userForm,
          permissions: { ...userForm.permissions, [key]: e.target.checked }
        })}
        className="w-4 h-4 mt-1 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
      />
      <div>
        <span className="text-sm font-medium text-slate-900">{label}</span>
        {description && (
          <p className="text-xs text-slate-500 mt-1">{description}</p>
        )}
      </div>
    </label>
  );

  const permissionGroups = {
    "Dashboard & Reporting": [
      { key: "view_dashboard", label: "View Dashboard", description: "Access to main dashboard and basic reports" },
      { key: "view_reports", label: "View Reports", description: "Access to detailed financial and operational reports" },
      { key: "export_data", label: "Export Data", description: "Download reports and data exports" }
    ],
    "Financial Management": [
      { key: "view_finances", label: "View Finances", description: "Access to financial data and accounts" },
      { key: "manage_accounts_ledger", label: "Manage Accounts & Ledger", description: "Add/edit accounts and view ledger" },
      { key: "create_journal_entries", label: "Create Journal Entries", description: "Add new financial transactions" },
      { key: "approve_journal_entries", label: "Approve Journal Entries", description: "Review and approve pending entries" }
    ],
    "Company & Business Units": [
      { key: "manage_information", label: "Manage Information", description: "Edit company and business unit details" },
      { key: "manage_companies", label: "Manage Companies", description: "Create/edit/delete companies and subsidiaries" },
      { key: "manage_business_units", label: "Manage Business Units", description: "Create/edit/delete business units" }
    ],
    "User Management": [
      { key: "view_users", label: "View Users", description: "See list of users and their roles" },
      { key: "manage_users", label: "Manage Users", description: "Create/edit/delete users and permissions" }
    ],
    "Settings & Configuration": [
      { key: "manage_settings", label: "Manage Settings", description: "Access to system settings and configuration" },
      { key: "manage_api_keys", label: "Manage API Keys", description: "Add/edit/delete external API integrations" },
      { key: "manage_branding", label: "Manage Branding", description: "Customize company colors and branding" }
    ],
    "Inventory & Operations": [
      { key: "view_inventory", label: "View Inventory", description: "Access to inventory levels and items" },
      { key: "manage_inventory", label: "Manage Inventory", description: "Add/edit inventory items and movements" },
      { key: "manage_procurement", label: "Manage Procurement", description: "Handle purchase orders and vendor management" }
    ],
    "Administrative": [
      { key: "full_access", label: "Full Access (Admin)", description: "Complete access to all features and settings" }
    ]
  };

  // Company (subsidiary) edit handlers
  const handleEditCompany = (companyId) => {
    const companyToEdit = subsidiaries.find(c => c.id === companyId);
    if (companyToEdit) {
      setEditingCompany(companyId);
      setCompanyForm({
        name: companyToEdit.name,
        industry: companyToEdit.industry,
        tax_id: companyToEdit.tax_id || "",
        accounting_basis: companyToEdit.accounting_basis
      });
    }
  };

  const handleUpdateCompany = async (companyId) => {
    try {
      await axios.put(`${API}/companies/${companyId}`, companyForm, { headers });
      toast.success("Subsidiary updated successfully");
      setEditingCompany(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update subsidiary");
    }
  };

  const handleDeleteCompany = async (companyId) => {
    const companyToDelete = subsidiaries.find(c => c.id === companyId);
    if (!window.confirm(`Are you sure you want to delete "${companyToDelete?.name}"? This action will backup the data for 6 months and allow restoration.`)) {
      return;
    }
    
    try {
      await axios.post(`${API}/companies/${companyId}/soft-delete`, {}, { headers });
      toast.success("Subsidiary deleted and backed up for 6 months");
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete subsidiary");
    }
  };

  // CSV Import handlers
  const downloadAccountsTemplate = async () => {
    try {
      const response = await axios.get(`${API}/templates/accounts/download`, { 
        headers,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'accounts_template.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success("Accounts template downloaded successfully");
    } catch (error) {
      toast.error("Failed to download template");
    }
  };

  const downloadCashFlowsTemplate = async () => {
    try {
      const response = await axios.get(`${API}/templates/cashflows/download`, { 
        headers,
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'cashflows_template.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success("Cash flows template downloaded successfully");
    } catch (error) {
      toast.error("Failed to download template");
    }
  };

  const handleAccountsTemplateUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/accounts/upload-template?company_id=${company.id}`, formData, {
        headers: {
          ...headers,
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success(`${response.data.created_accounts} accounts created successfully`);
      if (response.data.errors.length > 0) {
        console.warn("Upload errors:", response.data.errors);
      }
      loadData(); // Refresh accounts
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload accounts template");
    } finally {
      setUploading(false);
      event.target.value = ''; // Reset file input
    }
  };

  const handleCashFlowsTemplateUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/cashflows/upload-template?company_id=${company.id}`, formData, {
        headers: {
          ...headers,
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success(`${response.data.created_cashflows} cash flows and ${response.data.created_journal_entries} journal entries created`);
      if (response.data.errors.length > 0) {
        console.warn("Upload errors:", response.data.errors);
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload cash flows template");
    } finally {
      setUploading(false);
      event.target.value = ''; // Reset file input
    }
  };

  const handleBankStatementUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/bank-statements/upload?company_id=${company.id}`, formData, {
        headers: {
          ...headers,
          'Content-Type': 'multipart/form-data',
        },
      });

      toast.success(`Bank statement uploaded with ${response.data.transactions_count} transactions`);
      if (response.data.errors.length > 0) {
        console.warn("Upload errors:", response.data.errors);
      }
      loadBankStatements();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to upload bank statement");
    } finally {
      setUploading(false);
      event.target.value = ''; // Reset file input
    }
  };

  const loadBankStatements = async () => {
    try {
      const response = await axios.get(`${API}/bank-statements?company_id=${company.id}`, { headers });
      setBankStatements(response.data);
    } catch (error) {
      console.error("Failed to load bank statements:", error);
    }
  };

  const loadBankTransactions = async (statementId) => {
    try {
      const response = await axios.get(`${API}/bank-statements/${statementId}/transactions`, { headers });
      setBankTransactions(response.data);
      setSelectedBankStatement(statementId);
      setShowCategorizationDialog(true);
    } catch (error) {
      toast.error("Failed to load bank transactions");
    }
  };

  const handleTransactionCategorization = async (transactionId, accountId, category, notes) => {
    try {
      await axios.post(`${API}/bank-transactions/categorize`, [{
        transaction_id: transactionId,
        account_id: accountId,
        category: category,
        notes: notes
      }], { headers });

      // Update local state
      setBankTransactions(prev => 
        prev.map(t => 
          t.id === transactionId 
            ? { ...t, account_id: accountId, category, notes, is_categorized: true }
            : t
        )
      );

      toast.success("Transaction categorized successfully");
    } catch (error) {
      toast.error("Failed to categorize transaction");
    }
  };

  const createJournalEntriesFromBankTransactions = async (statementId) => {
    try {
      const response = await axios.post(`${API}/bank-transactions/${statementId}/create-journal-entries`, {}, { headers });
      toast.success(`${response.data.created_entries} journal entries created from bank transactions`);
      loadBankTransactions(statementId); // Reload to update status
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create journal entries");
    }
  };

  const handleCancelCompanyEdit = () => {
    setEditingCompany(null);
    setCompanyForm({
      name: "",
      industry: "restaurant",
      tax_id: "",
      accounting_basis: "Accrual"
    });
  };

  // Business Unit edit handlers
  const handleEditBU = (buId) => {
    const buToEdit = businessUnits.find(bu => bu.id === buId);
    if (buToEdit) {
      setEditingBU(buId);
      setBUForm({
        name: buToEdit.name,
        code: buToEdit.code,
        description: buToEdit.description || "",
        manager_name: buToEdit.manager_name || "",
        parent_subsidiary_id: buToEdit.parent_subsidiary_id || "",
        consolidation_enabled: buToEdit.consolidation_enabled !== false
      });
    }
  };

  const handleUpdateBU = async (buId) => {
    try {
      await axios.put(`${API}/business-units/${buId}`, buForm, { headers });
      toast.success("Business unit updated successfully");
      setEditingBU(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update business unit");
    }
  };

  const handleDeleteBU = (buId) => {
    handleSoftDeleteBU(buId);
  };

  const handleCancelBUEdit = () => {
    setEditingBU(null);
    setBUForm({
      name: "",
      code: "",
      description: "",
      manager_name: "",
      parent_subsidiary_id: "",
      consolidation_enabled: true
    });
  };

  // User edit handlers
  const handleEditUser = (userId) => {
    const userToEdit = users.find(user => user.id === userId);
    if (userToEdit) {
      setEditingUser(userId);
      setUserForm({
        email: userToEdit.email,
        password: "", // Don't populate password for security
        name: userToEdit.name,
        role: userToEdit.role,
        permissions: userToEdit.permissions || {
          view_dashboard: true,
          view_reports: false,
          export_data: false,
          view_finances: false,
          manage_accounts_ledger: false,
          create_journal_entries: false,
          approve_journal_entries: false,
          manage_information: false,
          manage_companies: false,
          manage_business_units: false,
          view_users: false,
          manage_users: false,
          manage_settings: false,
          manage_api_keys: false,
          manage_branding: false,
          view_inventory: false,
          manage_inventory: false,
          manage_procurement: false,
          full_access: false
        }
      });
    }
  };

  const handleUpdateUser = async (userId) => {
    try {
      const updateData = {
        name: userForm.name,
        email: userForm.email,
        role: userForm.role,
        permissions: userForm.permissions
      };
      
      // Only include password if it was changed
      if (userForm.password) {
        updateData.password = userForm.password;
      }

      await axios.put(`${API}/users/${userId}`, updateData, { headers });
      toast.success("User updated successfully");
      setEditingUser(null);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update user");
    }
  };

  const handleCancelUserEdit = () => {
    setEditingUser(null);
    setUserForm({
      email: "",
      password: "",
      name: "",
      role: "Analyst",
      permissions: {
        view_dashboard: true,
        view_reports: false,
        export_data: false,
        view_finances: false,
        manage_accounts_ledger: false,
        create_journal_entries: false,
        approve_journal_entries: false,
        manage_information: false,
        manage_companies: false,
        manage_business_units: false,
        view_users: false,
        manage_users: false,
        manage_settings: false,
        manage_api_keys: false,
        manage_branding: false,
        view_inventory: false,
        manage_inventory: false,
        manage_procurement: false,
        full_access: false
      }
    });
  };

  // Business Unit soft delete handlers
  const handleSoftDeleteBU = async (buId) => {
    const buToDelete = businessUnits.find(bu => bu.id === buId);
    if (!window.confirm(`Are you sure you want to delete "${buToDelete?.name}"? This action will backup the data for 6 months and allow restoration.`)) {
      return;
    }
    
    try {
      await axios.post(`${API}/business-units/${buId}/soft-delete`, {}, { headers });
      toast.success("Business unit deleted and backed up for 6 months");
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete business unit");
    }
  };

  const handleRestoreBU = async (buId, buName) => {
    if (!window.confirm(`Are you sure you want to restore "${buName}"?`)) {
      return;
    }
    
    try {
      await axios.post(`${API}/business-units/${buId}/restore`, {}, { headers });
      toast.success(`Business unit "${buName}" has been restored successfully`);
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to restore business unit");
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
                    <div key={sub.id} className="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">
                      {editingCompany === sub.id ? (
                        // Edit mode
                        <div className="space-y-4">
                          <div className="flex items-center gap-3 mb-4">
                            <Building2 className="w-8 h-8 text-indigo-600" />
                            <h4 className="font-semibold text-slate-900">Editing Subsidiary</h4>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                              <input
                                type="text"
                                value={companyForm.name}
                                onChange={(e) => setCompanyForm({ ...companyForm, name: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Industry</label>
                              <select
                                value={companyForm.industry}
                                onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="restaurant">Restaurant</option>
                                <option value="retail">Retail</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Tax ID</label>
                              <input
                                type="text"
                                value={companyForm.tax_id}
                                onChange={(e) => setCompanyForm({ ...companyForm, tax_id: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="XX-XXXXXXX"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Accounting Basis</label>
                              <select
                                value={companyForm.accounting_basis}
                                onChange={(e) => setCompanyForm({ ...companyForm, accounting_basis: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="Accrual">Accrual</option>
                                <option value="Cash">Cash</option>
                              </select>
                            </div>
                          </div>
                          
                          <div className="flex justify-end gap-2 pt-2">
                            <Button 
                              type="button" 
                              variant="outline" 
                              onClick={handleCancelCompanyEdit}
                              className="flex items-center gap-2"
                            >
                              <X className="w-4 h-4" />
                              Cancel
                            </Button>
                            <Button 
                              onClick={() => handleUpdateCompany(sub.id)}
                              className="flex items-center gap-2"
                            >
                              <Save className="w-4 h-4" />
                              Save
                            </Button>
                          </div>
                        </div>
                      ) : (
                        // View mode
                        <div className="flex items-center justify-between">
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
                          <div className="flex items-center gap-3">
                            <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded">
                              Subsidiary
                            </span>
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEditCompany(sub.id)}
                                className="p-2 h-8 w-8"
                                title="Edit subsidiary"
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteCompany(sub.id)}
                                className="p-2 h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                                title="Delete subsidiary"
                              >
                                <Trash className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        </div>
                      )}
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
              <div className="flex gap-2">
                {deletedBusinessUnits.length > 0 && (
                  <Button 
                    variant="outline"
                    onClick={() => setShowDeletedBUsDialog(true)}
                    className="text-orange-600 hover:text-orange-700"
                    size="sm"
                  >
                    <RotateCcw className="w-4 h-4 mr-1" />
                    Deleted ({deletedBusinessUnits.length})
                  </Button>
                )}
              </div>
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
                    
                    {/* Consolidation Settings */}
                    <div className="border-t pt-4 mt-4">
                      <h4 className="font-semibold text-slate-900 mb-3">Consolidation Settings</h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>Parent Subsidiary</Label>
                          <select
                            value={buForm.parent_subsidiary_id}
                            onChange={(e) => setBUForm({ ...buForm, parent_subsidiary_id: e.target.value })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          >
                            <option value="">Select parent subsidiary...</option>
                            {subsidiaries.map((sub) => (
                              <option key={sub.id} value={sub.id}>{sub.name}</option>
                            ))}
                          </select>
                          <p className="text-xs text-slate-500 mt-1">
                            Business unit transactions will consolidate to this subsidiary
                          </p>
                        </div>
                        <div>
                          <label className="flex items-center gap-2 pt-6">
                            <input
                              type="checkbox"
                              checked={buForm.consolidation_enabled}
                              onChange={(e) => setBUForm({ ...buForm, consolidation_enabled: e.target.checked })}
                              className="w-4 h-4"
                            />
                            <span className="text-sm font-medium">Enable Consolidation</span>
                          </label>
                          <p className="text-xs text-slate-500 mt-1 ml-6">
                            Include this BU in consolidated reports
                          </p>
                        </div>
                      </div>
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
                    <div key={bu.id} className="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors">
                      {editingBU === bu.id ? (
                        // Edit mode
                        <div className="space-y-4">
                          <div className="flex items-center gap-3 mb-4">
                            <Briefcase className="w-6 h-6 text-indigo-600" />
                            <h4 className="font-semibold text-slate-900">Editing Business Unit</h4>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                              <input
                                type="text"
                                value={buForm.name}
                                onChange={(e) => setBUForm({ ...buForm, name: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Code</label>
                              <input
                                type="text"
                                value={buForm.code}
                                onChange={(e) => setBUForm({ ...buForm, code: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="BU-SALES"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                              <input
                                type="text"
                                value={buForm.description}
                                onChange={(e) => setBUForm({ ...buForm, description: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="Handles all sales operations"
                              />
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-slate-700 mb-1">Manager Name</label>
                              <input
                                type="text"
                                value={buForm.manager_name}
                                onChange={(e) => setBUForm({ ...buForm, manager_name: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="John Doe"
                              />
                            </div>
                          </div>
                          
                          {/* Consolidation Settings */}
                          <div className="border-t pt-4 mt-4">
                            <h5 className="font-medium text-slate-900 mb-3">Consolidation Settings</h5>
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Parent Subsidiary</label>
                                <select
                                  value={buForm.parent_subsidiary_id}
                                  onChange={(e) => setBUForm({ ...buForm, parent_subsidiary_id: e.target.value })}
                                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                  <option value="">Select parent subsidiary...</option>
                                  {subsidiaries.map((sub) => (
                                    <option key={sub.id} value={sub.id}>{sub.name}</option>
                                  ))}
                                </select>
                                <p className="text-xs text-slate-500 mt-1">
                                  Business unit transactions will consolidate to this subsidiary
                                </p>
                              </div>
                              <div>
                                <label className="flex items-center gap-2 pt-8">
                                  <input
                                    type="checkbox"
                                    checked={buForm.consolidation_enabled}
                                    onChange={(e) => setBUForm({ ...buForm, consolidation_enabled: e.target.checked })}
                                    className="w-4 h-4"
                                  />
                                  <span className="text-sm font-medium text-slate-700">Enable Consolidation</span>
                                </label>
                                <p className="text-xs text-slate-500 mt-1 ml-6">
                                  Include this BU in consolidated reports
                                </p>
                              </div>
                            </div>
                          </div>
                          
                          <div className="flex justify-end gap-2 pt-2">
                            <Button 
                              type="button" 
                              variant="outline" 
                              onClick={handleCancelBUEdit}
                              className="flex items-center gap-2"
                            >
                              <X className="w-4 h-4" />
                              Cancel
                            </Button>
                            <Button 
                              onClick={() => handleUpdateBU(bu.id)}
                              className="flex items-center gap-2"
                            >
                              <Save className="w-4 h-4" />
                              Save
                            </Button>
                          </div>
                        </div>
                      ) : (
                        // View mode
                        <div className="flex items-center justify-between">
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
                              {bu.parent_subsidiary_name && (
                                <div className="flex items-center gap-1 mt-1">
                                  <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                                    Consolidates to: {bu.parent_subsidiary_name}
                                  </span>
                                </div>
                              )}
                              {bu.consolidation_enabled === false && (
                                <div className="flex items-center gap-1 mt-1">
                                  <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                                    Consolidation Disabled
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-3">
                            {bu.manager_name && (
                              <div className="text-right">
                                <p className="text-xs font-medium text-slate-600">Manager</p>
                                <p className="text-sm text-slate-900">{bu.manager_name}</p>
                              </div>
                            )}
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEditBU(bu.id)}
                                className="p-2 h-8 w-8"
                                title="Edit business unit"
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDeleteBU(bu.id)}
                                className="p-2 h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                                title="Delete business unit"
                              >
                                <Trash className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
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

        {/* Users Tab */}
        <TabsContent value="users">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>User Management</CardTitle>
              <Dialog open={showUserDialog} onOpenChange={setShowUserDialog}>
                <DialogTrigger asChild>
                  <Button data-testid="create-user">
                    <Plus className="w-4 h-4 mr-2" />
                    Add User
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl">
                  <DialogHeader>
                    <DialogTitle>Create New User</DialogTitle>
                    <DialogDescription>
                      Add a user with specific permissions
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleCreateUser} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label>Name *</Label>
                        <Input
                          value={userForm.name}
                          onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                          required
                        />
                      </div>
                      <div>
                        <Label>Email *</Label>
                        <Input
                          type="email"
                          value={userForm.email}
                          onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                          required
                        />
                      </div>
                    </div>
                    <div>
                      <Label>Password *</Label>
                      <Input
                        type="password"
                        value={userForm.password}
                        onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                        required
                      />
                    </div>
                    <div>
                      <Label>Role</Label>
                      <select
                        value={userForm.role}
                        onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="Analyst">Analyst</option>
                        <option value="Store Manager">Store Manager</option>
                        <option value="Finance">Finance</option>
                        <option value="Ops">Operations</option>
                        <option value="Owner">Owner</option>
                      </select>
                    </div>
                    <div className="border-t pt-4">
                      <h4 className="font-semibold mb-3">Permissions</h4>
                      <div className="max-h-64 overflow-y-auto space-y-4">
                        {Object.entries(permissionGroups).map(([groupName, permissions]) => (
                          <div key={groupName} className="space-y-2">
                            <h5 className="text-sm font-semibold text-slate-700 border-b border-slate-200 pb-1">
                              {groupName}
                            </h5>
                            <div className="space-y-2 pl-2">
                              {permissions.map(permission => 
                                renderPermissionCheckbox(permission.key, permission.label, permission.description)
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="flex justify-end gap-2 pt-4">
                      <Button type="button" variant="outline" onClick={() => setShowUserDialog(false)}>
                        Cancel
                      </Button>
                      <Button type="submit">Create User</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {users.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-3 px-4 font-semibold text-slate-700">Name</th>
                        <th className="text-left py-3 px-4 font-semibold text-slate-700">Email</th>
                        <th className="text-left py-3 px-4 font-semibold text-slate-700">Role</th>
                        <th className="text-left py-3 px-4 font-semibold text-slate-700">Permissions</th>
                        <th className="text-left py-3 px-4 font-semibold text-slate-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id} className="border-b border-slate-100">
                          <td className="py-3 px-4 font-medium">{user.name}</td>
                          <td className="py-3 px-4 text-sm">{user.email}</td>
                          <td className="py-3 px-4 text-sm">{user.role}</td>
                          <td className="py-3 px-4 text-xs">
                            <div className="flex flex-wrap gap-1">
                              {user.permissions?.full_access && (
                                <span className="px-2 py-1 bg-red-100 text-red-700 rounded">Full Access</span>
                              )}
                              {user.permissions?.manage_users && (
                                <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded">Users</span>
                              )}
                              {user.permissions?.manage_companies && (
                                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">Companies</span>
                              )}
                              {user.permissions?.manage_accounts_ledger && (
                                <span className="px-2 py-1 bg-green-100 text-green-700 rounded">Ledger</span>
                              )}
                              {user.permissions?.view_finances && (
                                <span className="px-2 py-1 bg-yellow-100 text-yellow-700 rounded">Finance</span>
                              )}
                              {user.permissions?.view_dashboard && !user.permissions?.full_access && (
                                <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded">Dashboard</span>
                              )}
                              {(!user.permissions?.full_access && !user.permissions?.manage_users && !user.permissions?.manage_companies && !user.permissions?.manage_accounts_ledger && !user.permissions?.view_finances) && (
                                <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded">Limited</span>
                              )}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex gap-1">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEditUser(user.id)}
                                className="p-2 h-8 w-8"
                                title="Edit user"
                              >
                                <Edit className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="p-2 h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50"
                                onClick={() => handleDeleteUser(user.id)}
                                title="Delete user"
                              >
                                <Trash className="w-4 h-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-slate-500">No users yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* APIs Tab */}
        <TabsContent value="apis">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>API Keys & Extensions</CardTitle>
              <Dialog open={showAPIDialog} onOpenChange={setShowAPIDialog}>
                <DialogTrigger asChild>
                  <Button data-testid="add-api-key">
                    <Plus className="w-4 h-4 mr-2" />
                    Add API Key
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Add API Key</DialogTitle>
                    <DialogDescription>
                      Connect external services to {company.name}
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleCreateAPIKey} className="space-y-4">
                    <div>
                      <Label>Service Name *</Label>
                      <Input
                        value={apiForm.name}
                        onChange={(e) => setAPIForm({ ...apiForm, name: e.target.value })}
                        placeholder="Parrot POS - Main Store"
                        required
                      />
                    </div>
                    <div>
                      <Label>Service Type *</Label>
                      <select
                        value={apiForm.service_type}
                        onChange={(e) => setAPIForm({ ...apiForm, service_type: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      >
                        <option value="parrot_pos">Parrot POS</option>
                        <option value="stripe">Stripe Payments</option>
                        <option value="plaid">Plaid Banking</option>
                        <option value="square">Square POS</option>
                        <option value="shopify">Shopify</option>
                        <option value="quickbooks">QuickBooks</option>
                        <option value="other">Other</option>
                      </select>
                    </div>
                    <div>
                      <Label>API Key *</Label>
                      <Input
                        type="password"
                        value={apiForm.api_key}
                        onChange={(e) => setAPIForm({ ...apiForm, api_key: e.target.value })}
                        placeholder="pk_xxxxxxxxxxxxx"
                        required
                      />
                    </div>
                    <div>
                      <Label>API Secret (Optional)</Label>
                      <Input
                        type="password"
                        value={apiForm.api_secret}
                        onChange={(e) => setAPIForm({ ...apiForm, api_secret: e.target.value })}
                        placeholder="sk_xxxxxxxxxxxxx"
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" onClick={() => setShowAPIDialog(false)}>
                        Cancel
                      </Button>
                      <Button type="submit">Add API Key</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              {apiKeys.length > 0 ? (
                <div className="space-y-3">
                  {apiKeys.map((key) => (
                    <div
                      key={key.id}
                      className="flex items-center justify-between p-4 border border-slate-200 rounded-lg"
                    >
                      <div>
                        <h4 className="font-semibold text-slate-900">{key.name}</h4>
                        <p className="text-sm text-slate-600 capitalize">{key.service_type.replace('_', ' ')}</p>
                        <p className="text-xs font-mono text-slate-500 mt-1">{key.api_key_masked}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-1 text-xs font-medium rounded ${
                          key.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                        }`}>
                          {key.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-600"
                          onClick={() => handleDeleteAPIKey(key.id)}
                        >
                          <Trash className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <p className="text-slate-500">No API keys configured</p>
                  <p className="text-sm text-slate-400 mt-2">Add API keys to connect external services</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding">
          <Card>
            <CardHeader>
              <CardTitle>Company Branding</CardTitle>
              <p className="text-sm text-slate-600">Customize the look and feel for {company.name}</p>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpdateBranding} className="space-y-6">
                <div>
                  <Label>Company Logo</Label>
                  <div className="space-y-3">
                    {/* File Upload */}
                    <div>
                      <label 
                        htmlFor="logo-upload" 
                        className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-slate-300 rounded-lg cursor-pointer hover:border-blue-400 transition-colors"
                      >
                        <Upload className="w-5 h-5 text-slate-600" />
                        <span className="text-sm font-medium text-slate-700">
                          Upload Logo (JPG or PNG)
                        </span>
                      </label>
                      <input
                        id="logo-upload"
                        type="file"
                        accept=".jpg,.jpeg,.png"
                        onChange={handleLogoUpload}
                        className="hidden"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        Max file size: 5MB. Recommended: 200x50px transparent PNG
                      </p>
                    </div>

                    {/* OR divider */}
                    <div className="flex items-center gap-3">
                      <div className="flex-1 border-t border-slate-300"></div>
                      <span className="text-xs text-slate-500">OR</span>
                      <div className="flex-1 border-t border-slate-300"></div>
                    </div>

                    {/* URL Input */}
                    <div>
                      <Input
                        value={brandingForm.logo_url}
                        onChange={(e) => setBrandingForm({ ...brandingForm, logo_url: e.target.value })}
                        placeholder="https://example.com/logo.png"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        Or enter a URL to your logo hosted elsewhere
                      </p>
                    </div>

                    {/* Preview */}
                    {brandingForm.logo_url && (
                      <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                        <p className="text-sm font-medium text-slate-700 mb-2">Logo Preview:</p>
                        <div className="bg-white p-3 rounded inline-block">
                          <img 
                            src={brandingForm.logo_url.startsWith('/') ? `${BACKEND_URL}${brandingForm.logo_url}` : brandingForm.logo_url}
                            alt="Logo preview" 
                            className="h-12 object-contain"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.parentElement.innerHTML = '<p class="text-red-600 text-sm">Failed to load logo</p>';
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label>Primary Color</Label>
                    <div className="flex gap-2 items-center">
                      <Input
                        type="color"
                        value={brandingForm.primary_color}
                        onChange={(e) => setBrandingForm({ ...brandingForm, primary_color: e.target.value })}
                        className="w-16 h-10"
                      />
                      <Input
                        value={brandingForm.primary_color}
                        onChange={(e) => setBrandingForm({ ...brandingForm, primary_color: e.target.value })}
                        placeholder="#3b82f6"
                        className="flex-1"
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Secondary Color</Label>
                    <div className="flex gap-2 items-center">
                      <Input
                        type="color"
                        value={brandingForm.secondary_color}
                        onChange={(e) => setBrandingForm({ ...brandingForm, secondary_color: e.target.value })}
                        className="w-16 h-10"
                      />
                      <Input
                        value={brandingForm.secondary_color}
                        onChange={(e) => setBrandingForm({ ...brandingForm, secondary_color: e.target.value })}
                        placeholder="#8b5cf6"
                        className="flex-1"
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Accent Color</Label>
                    <div className="flex gap-2 items-center">
                      <Input
                        type="color"
                        value={brandingForm.accent_color}
                        onChange={(e) => setBrandingForm({ ...brandingForm, accent_color: e.target.value })}
                        className="w-16 h-10"
                      />
                      <Input
                        value={brandingForm.accent_color}
                        onChange={(e) => setBrandingForm({ ...brandingForm, accent_color: e.target.value })}
                        placeholder="#10b981"
                        className="flex-1"
                      />
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-50 rounded-lg">
                  <h4 className="font-semibold mb-3">Color Preview</h4>
                  <div className="flex gap-3">
                    <div 
                      className="w-20 h-20 rounded"
                      style={{ backgroundColor: brandingForm.primary_color }}
                    />
                    <div 
                      className="w-20 h-20 rounded"
                      style={{ backgroundColor: brandingForm.secondary_color }}
                    />
                    <div 
                      className="w-20 h-20 rounded"
                      style={{ backgroundColor: brandingForm.accent_color }}
                    />
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button type="submit">Save Branding</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

 
      </Tabs>

      {/* User Edit Dialog */}
      <Dialog open={!!editingUser} onOpenChange={() => setEditingUser(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
            <DialogDescription>
              Update user details and permissions
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => { e.preventDefault(); handleUpdateUser(editingUser); }} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Name *</Label>
                <Input
                  value={userForm.name}
                  onChange={(e) => setUserForm({ ...userForm, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>New Password (leave blank to keep current)</Label>
                <Input
                  type="password"
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  placeholder="Leave blank to keep current password"
                />
              </div>
              <div>
                <Label>Role</Label>
                <select
                  value={userForm.role}
                  onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="Analyst">Analyst</option>
                  <option value="Store Manager">Store Manager</option>
                  <option value="Finance">Finance</option>
                  <option value="Ops">Operations</option>
                  <option value="Owner">Owner</option>
                </select>
              </div>
            </div>
            <div className="border-t pt-4">
              <h4 className="font-semibold mb-3">Permissions</h4>
              <div className="max-h-64 overflow-y-auto space-y-4">
                {Object.entries(permissionGroups).map(([groupName, permissions]) => (
                  <div key={groupName} className="space-y-2">
                    <h5 className="text-sm font-semibold text-slate-700 border-b border-slate-200 pb-1">
                      {groupName}
                    </h5>
                    <div className="space-y-2 pl-2">
                      {permissions.map(permission => 
                        renderPermissionCheckbox(permission.key, permission.label, permission.description)
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="outline" onClick={handleCancelUserEdit}>
                Cancel
              </Button>
              <Button type="submit">Update User</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Deleted Business Units Dialog */}
      <Dialog open={showDeletedBUsDialog} onOpenChange={setShowDeletedBUsDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RotateCcw className="w-5 h-5 text-orange-600" />
              Deleted Business Units
            </DialogTitle>
            <DialogDescription>
              Business units deleted within the last 6 months that can be restored
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {deletedBusinessUnits.map((bu) => (
              <div key={bu.id} className="border border-orange-200 rounded-lg p-4 bg-orange-50">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                      <Briefcase className="w-5 h-5 text-orange-600" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-900">{bu.name}</h4>
                      <p className="text-sm text-slate-600">{bu.company_name} • Code: {bu.code}</p>
                      <p className="text-xs text-slate-500 mt-1">
                        Deleted: {new Date(bu.deleted_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="mb-2">
                      <span className="text-xs font-medium text-slate-600">Days remaining:</span>
                      <div className={`text-sm font-bold ${
                        bu.days_remaining > 30 ? 'text-green-600' : 
                        bu.days_remaining > 7 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {bu.days_remaining} days
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => handleRestoreBU(bu.id, bu.name)}
                      className="bg-green-600 hover:bg-green-700 text-white"
                    >
                      <RotateCcw className="w-4 h-4 mr-1" />
                      Restore
                    </Button>
                  </div>
                </div>
              </div>
            ))}
            
            {deletedBusinessUnits.length === 0 && (
              <div className="text-center py-8">
                <p className="text-slate-500">No deleted business units available for restoration</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Bank Transaction Categorization Dialog */}
      <Dialog open={showCategorizationDialog} onOpenChange={setShowCategorizationDialog}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-auto">
          <DialogHeader>
            <DialogTitle>Categorize Bank Transactions</DialogTitle>
            <DialogDescription>
              Assign each transaction to an account for proper financial tracking
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {bankTransactions.map((transaction) => (
              <div key={transaction.id} className={`p-4 border rounded-lg ${
                transaction.is_categorized ? 'bg-green-50 border-green-200' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className="grid grid-cols-4 gap-4 items-center">
                  <div>
                    <p className="font-medium">{new Date(transaction.transaction_date).toLocaleDateString()}</p>
                    <p className="text-sm text-slate-600">{transaction.description}</p>
                  </div>
                  
                  <div className="text-center">
                    <span className={`font-bold ${
                      transaction.transaction_type === 'credit' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {transaction.transaction_type === 'credit' ? '+' : '-'}${transaction.amount.toFixed(2)}
                    </span>
                    <p className="text-xs text-slate-500 capitalize">{transaction.transaction_type}</p>
                  </div>
                  
                  <div>
                    {transaction.is_categorized ? (
                      <div>
                        <p className="font-medium text-green-700">{transaction.account_name}</p>
                        {transaction.category && (
                          <p className="text-sm text-slate-600">{transaction.category}</p>
                        )}
                      </div>
                    ) : (
                      <select
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                        onChange={(e) => {
                          if (e.target.value) {
                            const [accountId, accountName] = e.target.value.split('|');
                            handleTransactionCategorization(
                              transaction.id,
                              accountId,
                              accountName,
                              ''
                            );
                          }
                        }}
                        defaultValue=""
                      >
                        <option value="">Select Account...</option>
                        {accounts.map((account) => (
                          <option key={account.id} value={`${account.id}|${account.name}`}>
                            {account.name} ({account.account_type})
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  
                  <div className="text-center">
                    {transaction.is_categorized ? (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded">
                        Categorized
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs font-medium rounded">
                        Pending
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {bankTransactions.length === 0 && (
              <div className="text-center py-8">
                <p className="text-slate-500">No transactions to categorize</p>
              </div>
            )}
          </div>
          
          <div className="flex justify-end gap-2 pt-4">
            <Button 
              variant="outline" 
              onClick={() => setShowCategorizationDialog(false)}
            >
              Close
            </Button>
            {bankTransactions.some(t => t.is_categorized) && (
              <Button 
                onClick={() => {
                  createJournalEntriesFromBankTransactions(selectedBankStatement);
                  setShowCategorizationDialog(false);
                }}
              >
                Create Journal Entries ({bankTransactions.filter(t => t.is_categorized).length} transactions)
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
