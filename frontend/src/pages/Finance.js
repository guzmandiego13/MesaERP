import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Download, Upload, Plus, Edit, Trash } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Finance() {
  const [pl, setPL] = useState(null);
  const [bs, setBS] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [journalEntries, setJournalEntries] = useState([]);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });
  
  // Account form state
  const [showAccountDialog, setShowAccountDialog] = useState(false);
  const [editingAccount, setEditingAccount] = useState(null);
  const [accountForm, setAccountForm] = useState({
    code: "",
    name: "",
    account_type: "Asset"
  });
  
  // Journal entry form state
  const [showJournalDialog, setShowJournalDialog] = useState(false);
  const [journalForm, setJournalForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    description: "",
    reference: "",
    lines: [
      { account_id: "", debit: 0, credit: 0, memo: "" },
      { account_id: "", debit: 0, credit: 0, memo: "" }
    ]
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadFinanceData();
    loadJournalEntries();
  }, [dateRange]);

  const loadFinanceData = async () => {
    try {
      const [plRes, bsRes, accountsRes] = await Promise.all([
        axios.get(`${API}/finance/pl?start_date=${dateRange.start}&end_date=${dateRange.end}`, { headers }),
        axios.get(`${API}/finance/balance-sheet?as_of_date=${dateRange.end}`, { headers }),
        axios.get(`${API}/finance/accounts`, { headers })
      ]);
      setPL(plRes.data);
      setBS(bsRes.data);
      setAccounts(accountsRes.data);
    } catch (error) {
      toast.error("Failed to load finance data");
    }
  };
  
  const loadJournalEntries = async () => {
    try {
      const response = await axios.get(
        `${API}/finance/journal-entries?start_date=${dateRange.start}&end_date=${dateRange.end}`,
        { headers }
      );
      setJournalEntries(response.data);
    } catch (error) {
      console.error("Failed to load journal entries", error);
    }
  };
  
  const handleCreateAccount = async (e) => {
    e.preventDefault();
    try {
      if (editingAccount) {
        await axios.put(`${API}/finance/accounts/${editingAccount.id}`, accountForm, { headers });
        toast.success("Account updated successfully");
      } else {
        await axios.post(`${API}/finance/accounts`, accountForm, { headers });
        toast.success("Account created successfully");
      }
      setShowAccountDialog(false);
      setEditingAccount(null);
      setAccountForm({ code: "", name: "", account_type: "Asset" });
      loadFinanceData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save account");
    }
  };
  
  const handleEditAccount = (account) => {
    setEditingAccount(account);
    setAccountForm({
      code: account.code,
      name: account.name,
      account_type: account.account_type
    });
    setShowAccountDialog(true);
  };
  
  const handleCreateJournalEntry = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/finance/journal-entries`, journalForm, { headers });
      toast.success("Journal entry created successfully");
      setShowJournalDialog(false);
      setJournalForm({
        entry_date: new Date().toISOString().split('T')[0],
        description: "",
        reference: "",
        lines: [
          { account_id: "", debit: 0, credit: 0, memo: "" },
          { account_id: "", debit: 0, credit: 0, memo: "" }
        ]
      });
      loadFinanceData();
      loadJournalEntries();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to create journal entry");
    }
  };
  
  const addJournalLine = () => {
    setJournalForm({
      ...journalForm,
      lines: [...journalForm.lines, { account_id: "", debit: 0, credit: 0, memo: "" }]
    });
  };
  
  const updateJournalLine = (index, field, value) => {
    const newLines = [...journalForm.lines];
    newLines[index][field] = value;
    setJournalForm({ ...journalForm, lines: newLines });
  };
  
  const removeJournalLine = (index) => {
    if (journalForm.lines.length > 2) {
      const newLines = journalForm.lines.filter((_, i) => i !== index);
      setJournalForm({ ...journalForm, lines: newLines });
    }
  };
  
  const calculateBalance = () => {
    const totalDebits = journalForm.lines.reduce((sum, line) => sum + parseFloat(line.debit || 0), 0);
    const totalCredits = journalForm.lines.reduce((sum, line) => sum + parseFloat(line.credit || 0), 0);
    return { totalDebits, totalCredits, balanced: Math.abs(totalDebits - totalCredits) < 0.01 };
  };

  const handleCSVUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Simple CSV parser
    const text = await file.text();
    const lines = text.split('\n').filter(l => l.trim());
    const headers = lines[0].split(',');
    
    const transactions = [];
    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',');
      if (values.length >= 3) {
        transactions.push({
          date: values[0].trim(),
          description: values[1].trim(),
          amount: parseFloat(values[2].trim()),
          transaction_type: parseFloat(values[2]) < 0 ? "debit" : "credit"
        });
      }
    }

    try {
      await axios.post(`${API}/finance/bank-import`, transactions, { headers });
      toast.success(`Imported ${transactions.length} transactions`);
      loadFinanceData();
    } catch (error) {
      toast.error("Import failed");
    }
  };

  return (
    <div className="p-8 space-y-6" data-testid="finance-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Finance</h1>
          <p className="text-slate-600 mt-1">Financial statements and reporting</p>
        </div>
        <div className="flex gap-3">
          <Dialog open={showJournalDialog} onOpenChange={setShowJournalDialog}>
            <DialogTrigger asChild>
              <Button data-testid="create-journal-entry">
                <Plus className="w-4 h-4 mr-2" />
                New Journal Entry
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create Journal Entry</DialogTitle>
                <DialogDescription>Add a manual journal entry to adjust account balances</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreateJournalEntry} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Date</Label>
                    <Input
                      type="date"
                      value={journalForm.entry_date}
                      onChange={(e) => setJournalForm({ ...journalForm, entry_date: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <Label>Reference (Optional)</Label>
                    <Input
                      value={journalForm.reference}
                      onChange={(e) => setJournalForm({ ...journalForm, reference: e.target.value })}
                      placeholder="Invoice #, etc."
                    />
                  </div>
                </div>
                <div>
                  <Label>Description</Label>
                  <Input
                    value={journalForm.description}
                    onChange={(e) => setJournalForm({ ...journalForm, description: e.target.value })}
                    placeholder="Adjustment for..."
                    required
                  />
                </div>
                
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center mb-3">
                    <h4 className="font-semibold">Journal Lines</h4>
                    <Button type="button" size="sm" variant="outline" onClick={addJournalLine}>
                      <Plus className="w-4 h-4 mr-1" />
                      Add Line
                    </Button>
                  </div>
                  
                  {journalForm.lines.map((line, index) => (
                    <div key={index} className="grid grid-cols-12 gap-2 mb-2">
                      <div className="col-span-5">
                        <select
                          value={line.account_id}
                          onChange={(e) => updateJournalLine(index, 'account_id', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                          required
                        >
                          <option value="">Select Account</option>
                          {accounts.map((acc) => (
                            <option key={acc.id} value={acc.id}>
                              {acc.code} - {acc.name}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Debit"
                          value={line.debit}
                          onChange={(e) => updateJournalLine(index, 'debit', e.target.value)}
                          className="text-sm"
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Credit"
                          value={line.credit}
                          onChange={(e) => updateJournalLine(index, 'credit', e.target.value)}
                          className="text-sm"
                        />
                      </div>
                      <div className="col-span-2">
                        <Input
                          placeholder="Memo"
                          value={line.memo}
                          onChange={(e) => updateJournalLine(index, 'memo', e.target.value)}
                          className="text-sm"
                        />
                      </div>
                      <div className="col-span-1 flex items-center">
                        {journalForm.lines.length > 2 && (
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => removeJournalLine(index)}
                          >
                            <Trash className="w-4 h-4 text-red-600" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                  
                  <div className="mt-4 p-3 bg-slate-50 rounded">
                    {(() => {
                      const { totalDebits, totalCredits, balanced } = calculateBalance();
                      return (
                        <div className="flex justify-between items-center">
                          <div className="text-sm">
                            <span className="font-medium">Total Debits:</span> ${totalDebits.toFixed(2)}
                            <span className="mx-3">|</span>
                            <span className="font-medium">Total Credits:</span> ${totalCredits.toFixed(2)}
                          </div>
                          <div className={`text-sm font-semibold ${balanced ? 'text-green-600' : 'text-red-600'}`}>
                            {balanced ? '✓ Balanced' : '✗ Not Balanced'}
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                </div>
                
                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowJournalDialog(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={!calculateBalance().balanced}>
                    Create Entry
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
          
          <Button variant="outline" onClick={() => document.getElementById('csv-upload').click()} data-testid="import-bank-csv">
            <Upload className="w-4 h-4 mr-2" />
            Import Bank CSV
          </Button>
          <input
            id="csv-upload"
            type="file"
            accept=".csv"
            onChange={handleCSVUpload}
            className="hidden"
          />
        </div>
      </div>

      {/* Date Range Picker */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4 items-end">
            <div>
              <label className="text-sm font-medium text-slate-700">Start Date</label>
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md"
                data-testid="start-date"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">End Date</label>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="mt-1 block w-full px-3 py-2 border border-slate-300 rounded-md"
                data-testid="end-date"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="pl" className="w-full">
        <TabsList>
          <TabsTrigger value="pl" data-testid="tab-pl">Profit & Loss</TabsTrigger>
          <TabsTrigger value="bs" data-testid="tab-bs">Balance Sheet</TabsTrigger>
          <TabsTrigger value="coa" data-testid="tab-coa">Chart of Accounts</TabsTrigger>
        </TabsList>

        <TabsContent value="pl">
          <Card data-testid="pl-statement">
            <CardHeader>
              <CardTitle>Profit & Loss Statement</CardTitle>
              <p className="text-sm text-slate-600">
                Period: {dateRange.start} to {dateRange.end}
              </p>
            </CardHeader>
            <CardContent>
              {pl ? (
                <div className="space-y-6">
                  {/* Revenue Section */}
                  <div>
                    <h3 className="font-semibold text-lg text-slate-900 mb-3">Revenue</h3>
                    <div className="space-y-2">
                      {pl.revenue_detail?.map((item, idx) => (
                        <div key={idx} className="flex justify-between text-slate-700">
                          <span className="pl-4">{item.account}</span>
                          <span className="font-mono">${item.amount.toFixed(2)}</span>
                        </div>
                      ))}
                      <div className="flex justify-between font-semibold text-slate-900 pt-2 border-t">
                        <span>Total Revenue</span>
                        <span className="font-mono">${pl.revenue.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Expenses Section */}
                  <div>
                    <h3 className="font-semibold text-lg text-slate-900 mb-3">Expenses</h3>
                    <div className="space-y-2">
                      {pl.expense_detail?.map((item, idx) => (
                        <div key={idx} className="flex justify-between text-slate-700">
                          <span className="pl-4">{item.account}</span>
                          <span className="font-mono">${item.amount.toFixed(2)}</span>
                        </div>
                      ))}
                      <div className="flex justify-between font-semibold text-slate-900 pt-2 border-t">
                        <span>Total Expenses</span>
                        <span className="font-mono">${pl.expenses.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Net Income */}
                  <div className="flex justify-between font-bold text-xl pt-4 border-t-2 border-slate-300">
                    <span>Net Income</span>
                    <span className={`font-mono ${pl.net_income >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ${pl.net_income.toFixed(2)}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-slate-500">No data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="bs">
          <Card data-testid="bs-statement">
            <CardHeader>
              <CardTitle>Balance Sheet</CardTitle>
              <p className="text-sm text-slate-600">As of {dateRange.end}</p>
            </CardHeader>
            <CardContent>
              {bs ? (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div>
                      <h3 className="font-semibold text-lg text-slate-900 mb-3">Assets</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between font-semibold text-slate-900">
                          <span>Total Assets</span>
                          <span className="font-mono">${bs.assets.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h3 className="font-semibold text-lg text-slate-900 mb-3">Liabilities & Equity</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between text-slate-700">
                          <span className="pl-4">Liabilities</span>
                          <span className="font-mono">${bs.liabilities.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-slate-700">
                          <span className="pl-4">Equity</span>
                          <span className="font-mono">${bs.equity.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between font-semibold text-slate-900 pt-2 border-t">
                          <span>Total</span>
                          <span className="font-mono">${(bs.liabilities + bs.equity).toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-slate-500">No data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="coa">
          <Card data-testid="coa-list">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Chart of Accounts</CardTitle>
              <Dialog open={showAccountDialog} onOpenChange={setShowAccountDialog}>
                <DialogTrigger asChild>
                  <Button size="sm" onClick={() => {
                    setEditingAccount(null);
                    setAccountForm({ code: "", name: "", account_type: "Asset" });
                  }}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Account
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>{editingAccount ? 'Edit Account' : 'Add New Account'}</DialogTitle>
                    <DialogDescription>
                      {editingAccount ? 'Update account details' : 'Create a new account in your chart of accounts'}
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleCreateAccount} className="space-y-4">
                    <div>
                      <Label htmlFor="account-code">Account Code</Label>
                      <Input
                        id="account-code"
                        value={accountForm.code}
                        onChange={(e) => setAccountForm({ ...accountForm, code: e.target.value })}
                        placeholder="1000"
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="account-name">Account Name</Label>
                      <Input
                        id="account-name"
                        value={accountForm.name}
                        onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })}
                        placeholder="Cash in Bank"
                        required
                      />
                    </div>
                    <div>
                      <Label htmlFor="account-type">Account Type</Label>
                      <select
                        id="account-type"
                        value={accountForm.account_type}
                        onChange={(e) => setAccountForm({ ...accountForm, account_type: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md"
                        required
                      >
                        <option value="Asset">Asset</option>
                        <option value="Liability">Liability</option>
                        <option value="Equity">Equity</option>
                        <option value="Revenue">Revenue</option>
                        <option value="Expense">Expense</option>
                      </select>
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" onClick={() => setShowAccountDialog(false)}>
                        Cancel
                      </Button>
                      <Button type="submit">
                        {editingAccount ? 'Update' : 'Create'} Account
                      </Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Code</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Account Name</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Type</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Status</th>
                      <th className="text-left py-3 px-4 font-semibold text-slate-700">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {accounts.map((account) => (
                      <tr key={account.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4 font-mono text-slate-900">{account.code}</td>
                        <td className="py-3 px-4 text-slate-900">{account.name}</td>
                        <td className="py-3 px-4 text-slate-600">{account.account_type}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            account.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {account.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEditAccount(account)}
                            data-testid={`edit-account-${account.id}`}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
