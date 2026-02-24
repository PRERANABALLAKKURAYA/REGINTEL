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
  stakeholders_affected: string[];
}

export default function UpdateDetailPage() {
  const params = useParams();
  const id = params.id as string;
  
  const [update, setUpdate] = useState<Update | null>(null);
  const [authority, setAuthority] = useState<Authority | null>(null);
  const [aiSummary, setAiSummary] = useState<AISummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [summaryMode, setSummaryMode] = useState<"beginner" | "professional" | "legal">("professional");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const updateRes = await api.get(`/updates/${id}`);
        setUpdate(updateRes.data);

        const summaryRes = await api.post("/ai/summarize", {
          update_id: id,
          mode: summaryMode,
        });
        setAiSummary(summaryRes.data);

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
  }, [id, summaryMode]);

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
              <h1 className="text-4xl font-bold text-white">{update.title}</h1>
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
              className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                summaryMode === mode
                  ? "bg-[#00d9ff] text-[#0b152b]"
                  : "bg-white/10 text-[#aaa] hover:bg-white/20"
              }`}
            >
              {mode === "beginner" ? "🎓 Beginner" : mode === "professional" ? "💼 Professional" : "⚖️ Legal"}
            </button>
          ))}
        </div>

        {/* AI Summary */}
        {aiSummary && (
          <div className="card p-8 border border-white/10 space-y-6">
            <div>
              <h2 className="text-2xl font-bold text-white mb-4">🤖 AI Analysis</h2>
              <p className="text-[#ccc] leading-relaxed">{aiSummary.summary}</p>
            </div>

            {aiSummary.action_items && aiSummary.action_items.length > 0 && (
              <div className="pt-6 border-t border-white/10">
                <h3 className="text-lg font-semibold text-white mb-3">✅ Action Items</h3>
                <ul className="space-y-2">
                  {aiSummary.action_items.map((item, i) => (
                    <li key={i} className="flex gap-3 text-[#ccc]">
                      <span className="text-[#00d9ff] flex-shrink-0">→</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {aiSummary.stakeholders_affected && aiSummary.stakeholders_affected.length > 0 && (
              <div className="pt-6 border-t border-white/10">
                <h3 className="text-lg font-semibold text-white mb-3">👥 Affected Stakeholders</h3>
                <div className="flex flex-wrap gap-2">
                  {aiSummary.stakeholders_affected.map((stakeholder, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 rounded-full text-xs font-medium bg-[#7f5af0]/20 text-[#b0a0ff]"
                    >
                      {stakeholder}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Original Summary */}
        {update.short_summary && (
          <div className="card p-8 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4">📝 Original Summary</h2>
            <p className="text-[#ccc]">{update.short_summary}</p>
          </div>
        )}

        {/* Actions */}
        <div className="card p-8 border border-white/10">
          <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#00d9ff] font-medium transition">
              📧 Email Summary
            </button>
            <button className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#00d9ff] font-medium transition">
              📥 Export to PDF
            </button>
            <button className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#7f5af0] font-medium transition">
              ⭐ Save for Later
            </button>
            <button className="px-4 py-3 rounded-lg bg-white/10 hover:bg-white/20 text-[#7f5af0] font-medium transition">
              🔔 Set Alert
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}