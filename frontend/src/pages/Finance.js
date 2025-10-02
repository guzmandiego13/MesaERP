import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";
import { Download, Upload } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Finance() {
  const [pl, setPL] = useState(null);
  const [bs, setBS] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadFinanceData();
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
            <CardHeader>
              <CardTitle>Chart of Accounts</CardTitle>
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
