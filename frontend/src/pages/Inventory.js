import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { TrendingUp, AlertTriangle, Package } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Inventory() {
  const [levels, setLevels] = useState([]);
  const [stockouts, setStockouts] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    loadInventory();
  }, []);

  const loadInventory = async () => {
    try {
      const [levelsRes, stockoutsRes, locationsRes] = await Promise.all([
        axios.get(`${API}/inventory/levels`, { headers }),
        axios.get(`${API}/inventory/stockouts`, { headers }),
        axios.get(`${API}/locations`, { headers })
      ]);
      setLevels(levelsRes.data);
      setStockouts(stockoutsRes.data);
      setLocations(locationsRes.data);
    } catch (error) {
      toast.error("Failed to load inventory");
    } finally {
      setLoading(false);
    }
  };

  const loadForecast = async (itemId, locationId) => {
    try {
      const response = await axios.get(
        `${API}/forecast/demand?item_id=${itemId}&location_id=${locationId}&days=14`,
        { headers }
      );
      setForecast(response.data);
    } catch (error) {
      toast.error("Failed to load forecast");
    }
  };

  const seedDemoData = async () => {
    try {
      await axios.post(`${API}/seed/demo-data`, {}, { headers });
      toast.success("Demo data created!");
      loadInventory();
    } catch (error) {
      toast.error("Failed to seed data");
    }
  };

  return (
    <div className="p-8 space-y-6" data-testid="inventory-page">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Inventory</h1>
          <p className="text-slate-600 mt-1">Stock levels and AI-powered forecasting</p>
        </div>
        {levels.length === 0 && (
          <Button onClick={seedDemoData} data-testid="seed-demo-data">
            <Package className="w-4 h-4 mr-2" />
            Create Demo Inventory
          </Button>
        )}
      </div>

      {/* Stockouts Alert */}
      {stockouts.length > 0 && (
        <Card className="border-red-200 bg-red-50" data-testid="stockouts-alert">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-900">
              <AlertTriangle className="w-5 h-5" />
              {stockouts.length} Item{stockouts.length > 1 ? 's' : ''} Below Minimum Level
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {stockouts.slice(0, 5).map((item, idx) => (
                <div key={idx} className="flex justify-between items-center p-3 bg-white rounded border border-red-100">
                  <div>
                    <p className="font-medium text-slate-900">{item.item_name}</p>
                    <p className="text-sm text-slate-600">SKU: {item.sku}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-slate-600">Current: {item.current_qty}</p>
                    <p className="text-sm text-red-600 font-medium">Min: {item.min_level}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Inventory Levels */}
      <Card data-testid="inventory-levels">
        <CardHeader>
          <CardTitle>Stock Levels</CardTitle>
        </CardHeader>
        <CardContent>
          {levels.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Item</th>
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">SKU</th>
                    <th className="text-right py-3 px-4 font-semibold text-slate-700">On Hand</th>
                    <th className="text-right py-3 px-4 font-semibold text-slate-700">Min</th>
                    <th className="text-right py-3 px-4 font-semibold text-slate-700">Max</th>
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Status</th>
                    <th className="text-left py-3 px-4 font-semibold text-slate-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {levels.map((level) => {
                    const isLow = level.quantity_on_hand < level.min_level;
                    const location = locations.find(l => l.id === level.location_id);
                    
                    return (
                      <tr key={level.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-slate-900">{level.item_name}</p>
                            <p className="text-xs text-slate-500">{location?.name}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-600">{level.item_sku}</td>
                        <td className="py-3 px-4 text-right font-medium text-slate-900">{level.quantity_on_hand}</td>
                        <td className="py-3 px-4 text-right text-slate-600">{level.min_level}</td>
                        <td className="py-3 px-4 text-right text-slate-600">{level.max_level}</td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            isLow ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                          }`}>
                            {isLow ? 'Low Stock' : 'OK'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedItem({ item_id: level.item_id, location_id: level.location_id, name: level.item_name });
                              loadForecast(level.item_id, level.location_id);
                            }}
                            data-testid={`forecast-${level.item_id}`}
                          >
                            <TrendingUp className="w-4 h-4 mr-1" />
                            Forecast
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">No inventory data available</p>
              <p className="text-sm text-slate-400 mt-2">Create demo inventory to get started</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* AI Forecast */}
      {forecast && selectedItem && (
        <Card data-testid="forecast-card">
          <CardHeader>
            <CardTitle>AI Demand Forecast: {selectedItem.name}</CardTitle>
            <p className="text-sm text-slate-600">Next 14 days prediction</p>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Forecast Chart */}
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={forecast.forecast}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="day" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#fff",
                      border: "1px solid #e2e8f0",
                      borderRadius: "8px"
                    }}
                  />
                  <Bar dataKey="predicted_quantity" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Drivers */}
            <div>
              <h4 className="font-semibold text-slate-900 mb-3">Top Forecast Drivers</h4>
              <div className="space-y-2">
                {forecast.drivers?.map((driver, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                    <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold text-sm">
                      {idx + 1}
                    </div>
                    <p className="text-slate-700">{driver}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Confidence & Reasoning */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-600">Confidence Level</p>
                <p className="text-2xl font-bold text-slate-900 capitalize mt-1">{forecast.confidence}</p>
              </div>
              <div className="p-4 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-600">AI Analysis</p>
                <p className="text-sm text-slate-700 mt-1">{forecast.reasoning}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
