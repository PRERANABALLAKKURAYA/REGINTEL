"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export default function Layout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<any>(null);
  const [showAlertModal, setShowAlertModal] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/auth");
    }
    setUser({ email: "user@company.com", name: "Regulatory Expert" });
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/auth");
  };

  // Check if route is active
  const isActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname === href || pathname.startsWith(href + "/");
  };

  const navItems = [
    { href: "/dashboard", label: "📊 Dashboard", icon: "📊" },
    { href: "/dashboard/chat", label: "💬 AI Chat", icon: "💬" },
    { href: "/dashboard/analytics", label: "📈 Analytics", icon: "📈" },
    { href: "/dashboard/reports", label: "📥 Reports", icon: "📥" },
    { href: "/dashboard/settings", label: "⚙️ Settings", icon: "⚙️" },
  ];

  return (
    <div className="flex h-screen bg-aurora text-foreground overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-gradient-to-b from-[#0b152b] to-[#0a0f1a] border-r border-white/10 overflow-y-auto flex flex-col">
        <div className="p-6 sticky top-0 bg-gradient-to-b from-[#0b152b] to-[#0a0f1a] border-b border-white/10">
          <div className="font-[var(--font-display)] text-2xl font-bold bg-gradient-to-r from-[#00d9ff] to-[#7f5af0] bg-clip-text text-transparent">
            RegIntel
          </div>
          <p className="text-xs text-[#888] mt-1">Pharmaceutical Intelligence</p>
        </div>

        <nav className="p-6 space-y-2 flex-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-4 py-2.5 rounded-lg font-semibold text-sm transition ${
                isActive(item.href)
                  ? "bg-[#1a2a4a] text-[#00d9ff]"
                  : "text-[#aaa] hover:bg-white/10 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* User Profile Card */}
        <div className="p-6 border-t border-white/10">
          <div className="glass p-4 rounded-lg mb-4">
            <p className="text-xs text-[#888]">Signed in as</p>
            <p className="text-sm font-semibold text-[#00d9ff] truncate mt-1">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full px-4 py-2 text-sm bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded-lg font-medium transition"
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="border-b border-white/10 bg-[rgba(11,21,43,0.4)] backdrop-blur">
          <div className="px-8 py-4 flex justify-between items-center">
            <h2 className="font-semibold text-xl">Regulatory Intelligence Platform</h2>
            <div className="flex items-center gap-4">
              <span className="text-xs px-3 py-1.5 bg-green-500/20 text-green-300 rounded-full font-medium animate-pulse">
                ● System Ready
              </span>
              <button onClick={() => setShowAlertModal(true)} className="text-xs px-4 py-2 bg-[var(--accent)] hover:opacity-90 rounded-lg font-semibold transition flex items-center gap-2">
                <span>🔔</span> New Alert
              </button>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-8 relative">
          {children}
        </main>
      </div>
    </div>
  );
}
