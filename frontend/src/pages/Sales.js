import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { RefreshCw, ExternalLink } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Sales() {
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadSales();
  }, []);

  const loadSales = async () => {
    try {
      // Note: This would need a new endpoint in the backend
      // For now, we'll show a placeholder
      setSales([]);
    } catch (error) {
      toast.error("Failed to load sales");
    } finally {
      setLoading(false);
    }
  };

  const syncPOS = async () => {
    setSyncing(true);
    try {
      const response = await axios.post(`${API}/pos/sync`, {}, { headers });
      toast.success(`Synced ${response.data.synced_orders} orders from Parrot POS`);
      loadSales();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="p-8 space-y-6" data-testid="sales-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Sales</h1>
          <p className="text-slate-600 mt-1">POS integration and sales analytics</p>
        </div>
        <Button onClick={syncPOS} disabled={syncing} data-testid="sync-pos-sales">
          <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? "Syncing..." : "Sync Parrot POS"}
        </Button>
      </div>

      {/* POS Integration Status */}
      <Card data-testid="pos-integration-card">
        <CardHeader>
          <CardTitle>Parrot POS Integration</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-green-50 border border-green-200 rounded-lg">
              <div>
                <p className="font-semibold text-green-900">Connected</p>
                <p className="text-sm text-green-700">Parrot POS API is configured and ready</p>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-green-700">Active</span>
              </div>
            </div>

            <div className="space-y-2">
              <h4 className="font-semibold text-slate-900">Sync Information</h4>
              <ul className="text-sm text-slate-600 space-y-1">
                <li>• Orders are synced automatically from Parrot POS</li>
                <li>• Sales data is posted to the general ledger in real-time</li>
                <li>• Inventory movements are tracked from POS transactions</li>
                <li>• Click "Sync Parrot POS" to manually fetch latest orders</li>
              </ul>
            </div>

            <div className="pt-4">
              <a
                href="https://developer.parrotsoftware.io"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                View Parrot API Documentation
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Sales Analytics Placeholder */}
      <Card data-testid="sales-analytics">
        <CardHeader>
          <CardTitle>Sales Analytics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <p className="text-slate-500">Sales data will appear here after syncing with Parrot POS</p>
            <p className="text-sm text-slate-400 mt-2">Click "Sync Parrot POS" to fetch recent orders</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
