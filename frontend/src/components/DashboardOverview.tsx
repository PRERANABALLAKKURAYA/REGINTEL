"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

interface UpdateItem {
  id: number;
  title: string;
  category: string;
  published_date: string;
  source_link: string;
  authority_id: number;
  short_summary?: string;
}

interface AuthorityItem {
  id: number;
  name: string;
  country: string;
}

interface NotificationItem {
  id: number;
  title: string;
  source_link: string;
  published_date: string;
  is_read: boolean;
  authority: string;
}

interface GamificationData {
  points: number;
  streak_days: number;
  weekly_reads: number;
  badges: string[];
}

const categoryChips = [
  "Drug Safety",
  "Clinical",
  "Manufacturing",
  "Devices",
  "Quality",
  "Guidance",
];

interface AlertModalState {
  isOpen: boolean;
  type: "configure" | "new" | null;
}

const getRiskColor = (category: string) => {
  const riskMap: Record<string, string> = {
    "Drug Safety": "from-red-500/20 to-red-500/10",
    Clinical: "from-amber-500/20 to-amber-500/10",
    Manufacturing: "from-blue-500/20 to-blue-500/10",
    Devices: "from-purple-500/20 to-purple-500/10",
    Quality: "from-cyan-500/20 to-cyan-500/10",
    Guidance: "from-green-500/20 to-green-500/10",
  };
  return riskMap[category] || "from-slate-500/20 to-slate-500/10";
};

const isHomepageSource = (url: string): boolean => {
  // Always show View Source link if the URL exists
  // Even homepage URLs can be useful to view the authority site
  return false;
};

export default function DashboardOverview() {
  const router = useRouter();
  const [updates, setUpdates] = useState<UpdateItem[]>([]);
  const [authorities, setAuthorities] = useState<AuthorityItem[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [gamification, setGamification] = useState<GamificationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAuthority, setSelectedAuthority] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [alertModal, setAlertModal] = useState<AlertModalState>({ isOpen: false, type: null });
  const [alertEmail, setAlertEmail] = useState("");
  const [alertKeywords, setAlertKeywords] = useState("");

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [updatesRes, authoritiesRes, notificationsRes, gamificationRes] = await Promise.all([
          api.get("/updates/homepage?limit=20"),
          api.get("/authorities/"),
          api.get("/notifications/"),
          api.get("/gamification/"),
        ]);
        console.log("[Dashboard] Fetched data:");
        console.log("  - Updates:", updatesRes.data.length);
        console.log("  - Notifications:", notificationsRes.data.length);
        console.log("  - First update summary:", updatesRes.data[0]?.short_summary);
        console.log("  - First update source_link:", updatesRes.data[0]?.source_link);
        console.log("  - First notification:", notificationsRes.data[0]);
        setUpdates(updatesRes.data);
        setAuthorities(authoritiesRes.data);
        setNotifications(notificationsRes.data);
        setGamification(gamificationRes.data);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  const authorityMap = useMemo(() => {
    return authorities.reduce((acc, authority) => {
      acc[authority.id] = authority.name;
      return acc;
    }, {} as Record<number, string>);
  }, [authorities]);

  const filteredUpdates = useMemo(() => {
    return updates.filter((update) => {
      const matchesSearch = [update.title, update.short_summary]
        .join(" ")
        .toLowerCase()
        .includes(searchTerm.toLowerCase());

      const matchesAuthority = selectedAuthority
        ? update.authority_id === selectedAuthority
        : true;

      const matchesCategory = selectedCategory
        ? update.category?.toLowerCase() === selectedCategory.toLowerCase()
        : true;

      return matchesSearch && matchesAuthority && matchesCategory;
    });
  }, [updates, searchTerm, selectedAuthority, selectedCategory]);

  const sortedUpdates = useMemo(() => {
    return [...filteredUpdates].sort(
      (a, b) => new Date(b.published_date).getTime() - new Date(a.published_date).getTime()
    );
  }, [filteredUpdates]);

  const recentUpdates = useMemo(() => sortedUpdates.slice(0, 15), [sortedUpdates]);

  const handleExploreUpdates = () => {
    router.push("/updates");
  };

  const handleExportReport = async () => {
    try {
      const csv = [
        ["Update Title", "Authority", "Category", "Published", "Link"],
        ...updates.map(u => [
          u.title,
          authorityMap[u.authority_id] || "Unknown",
          u.category,
          new Date(u.published_date).toLocaleDateString(),
          u.source_link
        ])
      ]
        .map(row => row.map(cell => `"${cell}"`).join(","))
        .join("\n");

      const blob = new Blob([csv], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `regulatory-updates-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error exporting report:", error);
    }
  };

  const handleSaveAlert = () => {
    const alertConfig = {
      email: alertEmail,
      keywords: alertKeywords.split(",").map(k => k.trim()).filter(k => k),
      createdAt: new Date().toISOString()
    };
    
    // Save to localStorage
    const existingAlerts = JSON.parse(localStorage.getItem("userAlerts") || "[]");
    existingAlerts.push(alertConfig);
    localStorage.setItem("userAlerts", JSON.stringify(existingAlerts));
    
    console.log("Alert saved:", alertConfig);
    
    // Reset form and close modal
    setAlertModal({ isOpen: false, type: null });
    setAlertEmail("");
    setAlertKeywords("");
  };

  return (
    <div className="relative mx-auto max-w-7xl">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#0b152b] via-[#1a2a4a] to-[#0a0f1a] p-10 md:p-16 text-white mb-8 fade-up">
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-0 right-0 w-96 h-96 bg-[#00d9ff] rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#7f5af0] rounded-full blur-3xl" />
        </div>
        <div className="relative z-10 max-w-2xl">
          <p className="text-xs uppercase tracking-[0.3em] text-[#00d9ff]">Welcome Back</p>
          <h1 className="mt-4 text-5xl md:text-6xl font-[var(--font-display)] font-bold">
            Regulatory Pulse
          </h1>
          <p className="mt-4 text-xl text-gray-300">
            Monitor 6 global authorities. Catch compliance changes in real-time. Leverage AI for instant analysis.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <button onClick={handleExploreUpdates} className="px-7 py-3.5 bg-[#00d9ff] text-[#0b152b] rounded-lg font-semibold hover:opacity-90 transition text-base">
              🚀 Explore Updates
            </button>
            <button onClick={() => setAlertModal({ isOpen: true, type: "new" })} className="px-7 py-3.5 bg-white/10 backdrop-blur border border-white/20 rounded-lg font-semibold hover:bg-white/20 transition text-base">
              ⚡ Create Alert
            </button>
          </div>
        </div>
      </section>

      {/* Stats Cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Total Updates", value: updates.length > 0 ? updates.length : "—", icon: "📋" },
          { label: "Authorities", value: authorities.length || 6, icon: "🌍" },
          { label: "This Week", value: updates.slice(0, 5).length || 0, icon: "📈" },
          { label: "System Status", value: "Live", icon: "🟢", color: "text-green-400" },
        ].map((stat, i) => (
          <div
            key={stat.label}
            className={`card p-5 fade-up stagger-${(i % 4) + 1} border border-white/10`}
          >
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[#888]">{stat.label}</p>
                <p className={`mt-2 text-3xl font-bold ${stat.color || "text-[#00d9ff]"}`}>
                  {stat.icon} {stat.value}
                </p>
              </div>
            </div>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Main Updates Section */}
        <div className="space-y-4">
          {/* Filters Card */}
          <div className="card p-4 border border-white/10 fade-up">
            <div className="flex flex-col gap-3">
              <div>
                <h2 className="text-lg font-semibold mb-2">Update Stream</h2>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="🔍 Search updates..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#00d9ff]"
                  />
                  <button
                    onClick={() => {
                      setSearchTerm("");
                      setSelectedAuthority(null);
                      setSelectedCategory(null);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-xs font-medium transition"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {/* Authority Filters */}
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[#888] mb-2">Authorities</p>
                <div className="flex flex-wrap gap-1.5">
                  {authorities.map((authority) => (
                    <button
                      key={authority.id}
                      onClick={() =>
                        setSelectedAuthority(
                          selectedAuthority === authority.id ? null : authority.id
                        )
                      }
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
                        selectedAuthority === authority.id
                          ? "bg-[#00d9ff] text-[#0b152b]"
                          : "bg-white/10 hover:bg-white/20 text-gray-300"
                      }`}
                    >
                      {authority.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Category Filters */}
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[#888] mb-2">Categories</p>
                <div className="flex flex-wrap gap-1.5">
                  {categoryChips.map((chip) => (
                    <button
                      key={chip}
                      onClick={() =>
                        setSelectedCategory(selectedCategory === chip ? null : chip)
                      }
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition ${
                        selectedCategory === chip
                          ? "bg-[#7f5af0] text-white"
                          : "bg-[#7f5af0]/20 hover:bg-[#7f5af0]/40 text-[#b0a0ff]"
                      }`}
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Updates List */}
          <div className="space-y-2" id="updates-section">
            {loading && (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-24 rounded-2xl bg-white/5 animate-pulse border border-white/10" />
                ))}
              </div>
            )}

            {!loading && recentUpdates.length === 0 && (
              <div className="rounded-2xl border border-dashed border-white/10 p-6 text-center text-xs text-[#888]">
                No updates match your filters. Try clearing filters.
              </div>
            )}

            {!loading &&
              recentUpdates.map((update, idx) => (
                <div
                  key={update.id}
                  className={`card p-3 border border-white/10 hover:border-[#00d9ff]/50 transition duration-300 hover:shadow-lg hover:shadow-[#00d9ff]/10 fade-up stagger-${(idx % 4) + 1}`}
                  style={{
                    backgroundImage: `linear-gradient(135deg, ${getRiskColor(
                      update.category
                    ).split(" ")[0].replace("from-", "")}10 0%, transparent 100%)`,
                  }}
                >
                  <div className="flex justify-between items-start gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs uppercase tracking-[0.2em] font-semibold text-[#00d9ff]">
                          {authorityMap[update.authority_id]}
                        </span>
                        <span className="text-xs text-[#666]">•</span>
                        <span className="text-xs text-[#888]">
                          {new Date(update.published_date).toLocaleDateString()}
                        </span>
                        <span className="text-xs text-[#666]">•</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded font-semibold ${getRiskColor(update.category).split(" ")[0].replace("from-", "bg-").replace(/\/.*/, "/30 text-").split(" ")[0]}`}>
                          {update.category}
                        </span>
                      </div>
                      <h3 className="mt-2 text-sm font-semibold text-white leading-snug">{update.title}</h3>
                      {update.short_summary ? (
                        <p className="mt-2 text-xs text-[#2a2a2a] leading-relaxed line-clamp-2">
                          {update.short_summary}
                        </p>
                      ) : (
                        <p className="mt-2 text-xs text-[#666] italic">
                          No summary available
                        </p>
                      )}
                    </div>
                    <div className="flex-shrink-0">
                      <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-[#00d9ff]/20 text-[#00d9ff]">
                        NEW
                      </span>
                    </div>
                  </div>

                  <div className="mt-2 flex flex-wrap gap-2">
                    {/* Only show View Source if URL is a specific page, not a homepage */}
                    {update.source_link && !isHomepageSource(update.source_link) && (
                      <a
                        href={update.source_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs font-medium text-[#00d9ff] hover:text-[#7f5af0] transition"
                      >
                        → View Source
                      </a>
                    )}
                    <Link
                      href={`/dashboard/update/${update.id}`}
                      className="text-xs font-medium text-[#7f5af0] hover:text-[#00d9ff] transition"
                    >
                      ✨ AI Analysis
                    </Link>
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-4">
          {/* Gamification Card */}
          <div className="card p-4 border border-white/10 fade-up bg-gradient-to-br from-[#7f5af0]/10 to-transparent">
            <h3 className="text-lg font-semibold mb-3">🏆 Achievements</h3>
            <div className="space-y-2">
              <div className="flex justify-between items-center p-2 rounded-lg bg-white/5">
                <span className="text-xs text-[#888]">Points</span>
                <span className="text-xl font-bold text-[#00d9ff]">{gamification?.points ?? 0}</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-white/5">
                <span className="text-xs text-[#888]">Streak</span>
                <span className="text-xl font-bold text-[#7f5af0]">{gamification?.streak_days ?? 0}🔥</span>
              </div>
              <div className="flex justify-between items-center p-2 rounded-lg bg-white/5">
                <span className="text-xs text-[#888]">This Week</span>
                <span className="text-xl font-bold text-[#00d9ff]">{gamification?.weekly_reads ?? 0}</span>
              </div>
              <div className="pt-2 border-t border-white/10">
                <p className="text-xs uppercase tracking-[0.2em] text-[#888] mb-1">Badges</p>
                <div className="flex flex-wrap gap-1">
                  {(gamification?.badges ?? ["Newcomer"]).map((badge) => (
                    <span
                      key={badge}
                      className="px-2 py-0.5 rounded-full text-xs font-semibold bg-[#00d9ff]/20 text-[#00d9ff]"
                    >
                      {badge}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Notifications Card */}
          <div className="card p-4 border border-white/10 fade-up">
            <h3 className="text-lg font-semibold mb-3">🔔 Alerts</h3>
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-16 rounded-lg bg-white/5 animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-4 rounded-lg bg-white/5 text-xs text-[#888] text-center">
                    No alerts available
                  </div>
                ) : (
                  notifications.slice(0, 5).map((note) => {
                    const card = (
                      <>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-semibold text-[#00d9ff]">{note.authority}</span>
                          <span className="text-xs text-[#666]">•</span>
                          <span className="text-xs text-[#888]">
                            {new Date(note.published_date).toLocaleDateString()}
                          </span>
                        </div>
                        <div className="text-sm font-medium text-[#0b152b] line-clamp-2">{note.title}</div>
                      </>
                    );

                    if (note.source_link && !isHomepageSource(note.source_link)) {
                      return (
                        <a
                          key={note.id}
                          href={note.source_link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#00d9ff]/50 transition"
                        >
                          {card}
                        </a>
                      );
                    }

                    return (
                      <div
                        key={note.id}
                        className="block p-3 rounded-lg bg-white/5 border border-white/10"
                      >
                        {card}
                      </div>
                    );
                  })
                )}
              </div>
            )}
            <button onClick={() => setAlertModal({ isOpen: true, type: "configure" })} className="w-full mt-2 px-3 py-2 bg-[#7f5af0] hover:bg-[#7f5af0]/80 rounded-lg text-xs font-semibold transition">
              ⚙️ Configure
            </button>
          </div>

          {/* Quick Actions */}
          <div className="card p-4 border border-white/10 fade-up">
            <h3 className="text-lg font-semibold mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <Link
                href="/dashboard/chat"
                className="block p-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-[#00d9ff] transition text-center"
              >
                💬 AI Chat
              </Link>
              <button onClick={handleExportReport} className="w-full p-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs font-medium text-[#7f5af0] transition">
                📥 Export
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Alert Modal */}
      {alertModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="card border border-white/20 p-8 max-w-md w-full mx-4">
            <h3 className="text-2xl font-semibold mb-4">
              {alertModal.type === "new" ? "⚡ Create Alert" : "⚙️ Configure Alerts"}
            </h3>
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium mb-2">Email Address</label>
                <input
                  type="email"
                  value={alertEmail}
                  onChange={(e) => setAlertEmail(e.target.value)}
                  placeholder="your@email.com"
                  className="w-full border border-white/10 rounded-lg px-4 py-2.5 bg-white/5 text-base placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00d9ff]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Keywords (comma separated)</label>
                <textarea
                  value={alertKeywords}
                  onChange={(e) => setAlertKeywords(e.target.value)}
                  placeholder="e.g., biosimilar, safety, warning"
                  className="w-full border border-white/10 rounded-lg px-4 py-2.5 bg-white/5 text-base placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#00d9ff] resize-none h-20"
                />
              </div>
              <div className="p-3 rounded-lg bg-[#00d9ff]/10 border border-[#00d9ff]/20">
                <p className="text-sm text-[#00d9ff]">You'll receive email notifications matching these keywords</p>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setAlertModal({ isOpen: false, type: null })}
                className="flex-1 px-4 py-2.5 rounded-lg bg-white/10 hover:bg-white/20 text-base font-semibold transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAlert}
                className="flex-1 px-4 py-2.5 rounded-lg bg-[#00d9ff] text-[#0b152b] text-base font-semibold hover:opacity-90 transition"
              >
                {alertModal.type === "new" ? "Create" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
