import { Outlet, Link, useLocation } from "react-router-dom";
import { LayoutDashboard, DollarSign, ShoppingCart, Package, FileText, LogOut, Building2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Layout({ user, tenant, onLogout }) {
  const location = useLocation();

  const navItems = [
    { path: "/", icon: LayoutDashboard, label: "Dashboard" },
    { path: "/finance", icon: DollarSign, label: "Finance" },
    { path: "/sales", icon: ShoppingCart, label: "Sales" },
    { path: "/inventory", icon: Package, label: "Inventory" },
    { path: "/procurement", icon: FileText, label: "Procurement" },
  ];

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col">
        <div className="p-6 border-b border-slate-200">
          <h1 className="text-2xl font-bold text-slate-900">MesaERP</h1>
          <div className="mt-3 flex items-center gap-2 text-sm text-slate-600">
            <Building2 className="w-4 h-4" />
            <span className="font-medium">{tenant?.name}</span>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="mb-3 px-2">
            <p className="text-sm font-medium text-slate-900">{user?.name}</p>
            <p className="text-xs text-slate-500">{user?.email}</p>
            <p className="text-xs text-blue-600 mt-1">{user?.role}</p>
          </div>
          <Button
            onClick={onLogout}
            variant="outline"
            className="w-full justify-start gap-2"
            data-testid="logout-button"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </Button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
