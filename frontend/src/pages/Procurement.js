import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Zap, FileText, CheckCircle } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Procurement() {
  const [pos, setPOs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadPOs();
  }, []);

  const loadPOs = async () => {
    try {
      const response = await axios.get(`${API}/procurement/pos`, { headers });
      setPOs(response.data);
    } catch (error) {
      toast.error("Failed to load purchase orders");
    } finally {
      setLoading(false);
    }
  };

  const autoGeneratePOs = async () => {
    setGenerating(true);
    try {
      const response = await axios.post(`${API}/procurement/auto-generate-pos`, {}, { headers });
      toast.success(`Generated ${response.data.pos_created} purchase orders`);
      loadPOs();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to generate POs");
    } finally {
      setGenerating(false);
    }
  };

  const updatePOStatus = async (poId, status) => {
    try {
      await axios.patch(`${API}/procurement/pos/${poId}/status`, { status }, {
        headers: { ...headers, 'Content-Type': 'application/json' }
      });
      toast.success(`PO status updated to ${status}`);
      loadPOs();
    } catch (error) {
      toast.error("Failed to update PO");
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      Draft: 'bg-gray-100 text-gray-700',
      Submitted: 'bg-blue-100 text-blue-700',
      Approved: 'bg-green-100 text-green-700',
      Sent: 'bg-purple-100 text-purple-700',
      Received: 'bg-emerald-100 text-emerald-700',
      Partial: 'bg-yellow-100 text-yellow-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div className="p-8 space-y-6" data-testid="procurement-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Procurement</h1>
          <p className="text-slate-600 mt-1">Purchase orders and auto-generation</p>
        </div>
        <Button onClick={autoGeneratePOs} disabled={generating} data-testid="auto-generate-pos">
          <Zap className={`w-4 h-4 mr-2 ${generating ? 'animate-pulse' : ''}`} />
          {generating ? "Generating..." : "Auto-Generate POs"}
        </Button>
      </div>

      {/* Auto-PO Info */}
      <Card data-testid="auto-po-info">
        <CardHeader>
          <CardTitle>AI-Powered Auto-PO Generation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <p className="text-slate-700">
              The system automatically generates purchase orders for items below their reorder point,
              using AI-powered demand forecasting to optimize order quantities.
            </p>
            <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
              <Zap className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <p className="font-medium text-blue-900">How it works:</p>
                <ul className="text-sm text-blue-800 mt-1 space-y-1">
                  <li>• Monitors inventory levels in real-time</li>
                  <li>• Triggers when stock falls below reorder point</li>
                  <li>• Calculates optimal order quantity using AI forecasting</li>
                  <li>• Creates draft PO for manager approval</li>
                  <li>• Considers lead times, MOQ, and service level targets</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Purchase Orders List */}
      <Card data-testid="po-list">
        <CardHeader>
          <CardTitle>Purchase Orders</CardTitle>
        </CardHeader>
        <CardContent>
          {pos.length > 0 ? (
            <div className="space-y-4">
              {pos.map((po) => (
                <div
                  key={po.id}
                  className="p-4 border border-slate-200 rounded-lg hover:border-slate-300 transition-colors"
                  data-testid={`po-${po.id}`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-3">
                        <h3 className="font-semibold text-lg text-slate-900">{po.po_number}</h3>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(po.status)}`}>
                          {po.status}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 mt-1">
                        {new Date(po.order_date).toLocaleDateString()}
                        {po.expected_delivery && (
                          <span className="ml-3">
                            Expected: {new Date(po.expected_delivery).toLocaleDateString()}
                          </span>
                        )}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-slate-900">${po.total_amount.toFixed(2)}</p>
                    </div>
                  </div>

                  {/* Line Items */}
                  <div className="mb-3">
                    <h4 className="text-sm font-medium text-slate-700 mb-2">Items:</h4>
                    <div className="space-y-1">
                      {po.line_items.map((item, idx) => (
                        <div key={idx} className="flex justify-between text-sm p-2 bg-slate-50 rounded">
                          <span className="text-slate-700">
                            {item.name} <span className="text-slate-500">(SKU: {item.sku})</span>
                          </span>
                          <span className="text-slate-900 font-medium">
                            {item.quantity} × ${item.unit_cost.toFixed(2)} = ${item.total.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {po.notes && (
                    <p className="text-sm text-slate-600 italic mb-3">{po.notes}</p>
                  )}

                  {/* Actions */}
                  {po.status === 'Draft' && (
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => updatePOStatus(po.id, 'Approved')}
                        data-testid={`approve-po-${po.id}`}
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve
                      </Button>
                    </div>
                  )}
                  {po.status === 'Approved' && (
                    <Button
                      size="sm"
                      onClick={() => updatePOStatus(po.id, 'Sent')}
                      data-testid={`send-po-${po.id}`}
                    >
                      Send to Vendor
                    </Button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">No purchase orders yet</p>
              <p className="text-sm text-slate-400 mt-2">Click "Auto-Generate POs" to create orders for low-stock items</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
