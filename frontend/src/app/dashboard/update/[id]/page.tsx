"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Layout from "@/components/Layout";
import api from "@/lib/api";
import Link from "next/link";

interface Update {
  id: number;
  title: string;
  category: string;
  published_date: string;
  source_link: string;
  authority_id: number;
  short_summary?: string;
}

interface Authority {
  id: number;
  name: string;
  country: string;
}

interface AISummary {
  summary: string;
  risk_level: string;
  action_items: string[];
}

export default function UpdateDetailPage() {
  const params = useParams();
  const id = params.id as string;
  
  const [update, setUpdate] = useState<Update | null>(null);
  const [authority, setAuthority] = useState<Authority | null>(null);
  const [aiSummary, setAiSummary] = useState<AISummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [summaryMode, setSummaryMode] = useState<"beginner" | "professional" | "legal">("professional");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string>("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [analysisCache, setAnalysisCache] = useState<Record<string, AISummary>>({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const updateRes = await api.get(`/updates/${id}`);
        setUpdate(updateRes.data);

        if (updateRes.data.authority_id) {
          const authorityRes = await api.get(`/authorities/${updateRes.data.authority_id}`);
          setAuthority(authorityRes.data);
        }
      } catch (error) {
        console.error("Failed to fetch update details:", error);
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchData();
    }
  }, [id]);

  useEffect(() => {
    const fetchAnalysis = async () => {
      const cacheKey = `${id}_${summaryMode}`;
      
      // Check cache first
      if (analysisCache[cacheKey]) {
        setAiSummary(analysisCache[cacheKey]);
        return;
      }

      setAnalysisLoading(true);
      try {
        const analysisRes = await api.post(`/updates/${id}/analyze`, {
          difficulty_level: summaryMode,
        });
        
        const newAnalysis = {
          summary: analysisRes.data.summary,
          risk_level: analysisRes.data.risk_level,
          action_items: analysisRes.data.action_items,
        };
        
        setAiSummary(newAnalysis);
        setAnalysisCache(prev => ({
          ...prev,
          [cacheKey]: newAnalysis,
        }));
      } catch (error) {
        console.error("Failed to fetch analysis:", error);
      } finally {
        setAnalysisLoading(false);
      }
    };

    if (id && update) {
      fetchAnalysis();
    }
  }, [id, summaryMode, update]);

  if (loading) {
    return (
      <Layout>
        <div className="text-center py-12">
          <div className="animate-spin text-4xl mb-4">⏳</div>
          <p className="text-[#888]">Loading regulatory update...</p>
        </div>
      </Layout>
    );
  }

  if (!update) {
    return (
      <Layout>
        <div className="text-center py-12">
          <p className="text-[#888] mb-4">Update not found</p>
          <Link href="/dashboard" className="text-[#00d9ff] hover:text-[#7f5af0]">
            ← Back to Dashboard
          </Link>
        </div>
      </Layout>
    );
  }

  const handleEmailSummary = async () => {
    setActionLoading("email");
    try {
      const email = recipientEmail || (localStorage.getItem("userEmail") || "user@example.com");
      const response = await api.post(`/updates/${id}/email`, {
        recipient_email: email,
      });
      setActionMessage("✅ Summary email sent!");
      setTimeout(() => setActionMessage(""), 3000);
    } catch (error) {
      setActionMessage("❌ Failed to send email");
      console.error("Email error:", error);
    } finally {
      setActionLoading(null);
      setShowEmailForm(false);
      setRecipientEmail("");
    }
  };

  const handleExportPDF = async () => {
    setActionLoading("pdf");
    try {
      const response = await api.post(`/updates/${id}/export-pdf`);
      setActionMessage("✅ PDF exported successfully!");
      // In production, trigger download
      setTimeout(() => setActionMessage(""), 3000);
    } catch (error) {
      setActionMessage("❌ Failed to export PDF");
      console.error("PDF error:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSaveForLater = async () => {
    setActionLoading("save");
    try {
      const response = await api.post(`/updates/${id}/save`);
      setActionMessage("⭐ Update saved for later!");
      setTimeout(() => setActionMessage(""), 3000);
    } catch (error) {
      setActionMessage("❌ Failed to save update");
      console.error("Save error:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleSetAlert = async () => {
    setActionLoading("alert");
    try {
      const response = await api.post(`/updates/${id}/alert`, {
        alert_type: "email",
      });
      setActionMessage("🔔 Alert set successfully!");
      setTimeout(() => setActionMessage(""), 3000);
    } catch (error) {
      setActionMessage("❌ Failed to set alert");
      console.error("Alert error:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const getRiskColor = () => {
    const risk = aiSummary?.risk_level?.toLowerCase() || "medium";
    if (risk.includes("high")) return "bg-red-500/20 text-red-300 border-red-500/50";
    if (risk.includes("low")) return "bg-green-500/20 text-green-300 border-green-500/50";
    return "bg-amber-500/20 text-amber-300 border-amber-500/50";
  };

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-[#888]">
          <Link href="/dashboard" className="hover:text-[#00d9ff]">Dashboard</Link>
          <span>→</span>
          <span>{authority?.name}</span>
        </div>

        {/* Header */}
        <div className="card p-8 border border-white/10">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex-1">
              <p className="text-xs uppercase tracking-[0.2em] text-[#00d9ff] mb-2">
                {authority?.name} • {new Date(update.published_date).toLocaleDateString()}
              </p>
              <h1 className="text-4xl font-bold text-black">{update.title}</h1>
            </div>
            <a
              href={update.source_link}
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 bg-[#00d9ff] text-[#0b152b] rounded-lg font-semibold hover:opacity-90 transition whitespace-nowrap"
            >
              📖 Official Source
            </a>
          </div>

          <div className="flex flex-wrap gap-2 mt-4">
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-[#7f5af0]/20 text-[#b0a0ff]">
              {update.category}
            </span>
            {aiSummary && (
              <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getRiskColor()}`}>
                🚨 {aiSummary.risk_level}
              </span>
            )}
          </div>
        </div>

        {/* Summary Modes */}
        <div className="flex gap-2 flex-wrap">
          {(["beginner", "professional", "legal"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setSummaryMode(mode)}
              disabled={analysisLoading}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                analysisLoading
                  ? "bg-white/5 text-[#555] cursor-not-allowed opacity-50"
                  : summaryMode === mode
                  ? "bg-[#00d9ff] text-[#0b152b]"
                  : "bg-white/10 text-[#aaa] hover:bg-white/20"
              }`}
            >
              {mode === "beginner" ? "🎓 Beginner" : mode === "professional" ? "💼 Professional" : "⚖️ Legal"}
            </button>
          ))}
        </div>

        {/* AI Summary */}
        {analysisLoading ? (
          <div className="card p-8 border border-white/10 flex items-center justify-center gap-3">
            <div className="animate-spin text-2xl">⏳</div>
            <p className="text-[#888]">Generating AI analysis...</p>
          </div>
        ) : aiSummary ? (
          <div className="card p-8 border border-white/10 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">🤖 AI Analysis</h2>
              <p className="text-black leading-relaxed text-base">{aiSummary.summary}</p>
            </div>

            {aiSummary.action_items && aiSummary.action_items.length > 0 && (
              <div className="pt-6 border-t border-white/10">
                <h3 className="text-lg font-semibold text-white mb-3">✅ Action Items</h3>
                <ul className="space-y-2">
                  {aiSummary.action_items.map((item, i) => (
                    <li key={i} className="flex gap-3 text-black">
                      <span className="text-[#00d9ff] flex-shrink-0">→</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}

        {/* Original Summary */}
        {update.short_summary && (
          <div className="card p-8 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4">📝 Original Summary</h2>
            <p className="text-black">{update.short_summary}</p>
          </div>
        )}

        {/* Actions */}
        <div className="card p-8 border border-white/10">
          <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>
          {actionMessage && (
            <div className="mb-4 p-3 rounded-lg bg-white/10 text-[#00d9ff] text-sm">
              {actionMessage}
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <button 
                onClick={() => setShowEmailForm(!showEmailForm)}
                disabled={actionLoading === "email"}
                className="w-full px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#00d9ff] font-medium transition disabled:opacity-50"
              >
                {actionLoading === "email" ? "⏳ Sending..." : "📧 Email Summary"}
              </button>
              {showEmailForm && (
                <div className="mt-2 p-3 bg-white/5 rounded-lg">
                  <input
                    type="email"
                    placeholder="Enter email"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    className="w-full px-2 py-1 bg-white/10 text-white text-sm rounded mb-2 outline-none focus:ring-1 focus:ring-[#00d9ff]"
                  />
                  <button
                    onClick={handleEmailSummary}
                    disabled={actionLoading === "email"}
                    className="w-full px-2 py-1 bg-[#00d9ff] text-[#0b152b] text-sm font-medium rounded hover:opacity-90 transition disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              )}
            </div>
            <button 
              onClick={handleExportPDF}
              disabled={actionLoading === "pdf"}
              className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#00d9ff] font-medium transition disabled:opacity-50"
            >
              {actionLoading === "pdf" ? "⏳ Exporting..." : "📥 Export to PDF"}
            </button>
            <button 
              onClick={handleSaveForLater}
              disabled={actionLoading === "save"}
              className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#7f5af0] font-medium transition disabled:opacity-50"
            >
              {actionLoading === "save" ? "⏳ Saving..." : "⭐ Save for Later"}
            </button>
            <button 
              onClick={handleSetAlert}
              disabled={actionLoading === "alert"}
              className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#7f5af0] font-medium transition disabled:opacity-50"
            >
              {actionLoading === "alert" ? "⏳ Setting..." : "🔔 Set Alert"}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
