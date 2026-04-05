"use client";

import React, { useEffect, useMemo, useState } from "react";
import Layout from "@/components/Layout";
import Link from "next/link";
import api from "@/lib/api";

interface AnalyticsData {
  totalQueries: number;
  totalAlerts: number;
  aiUsageCount: number;
  averageResponseTime: number;
  authorityActivity: { authority: string; count: number; latestUpdate?: string | null }[];
  categoryDistribution: { category: string; count: number }[];
  weeklyTrend: { day: string; queries: number; date: string }[];
  queryClassification: { type: string; count: number; percentage: number }[];
  freshness?: {
    latestUpdateDate?: string | null;
    latestUpdateTitle?: string | null;
    recent7DayCount: number;
    stalenessAlert: boolean;
  };
}

const formatDate = (value?: string | null) => {
  if (!value) return "Unknown";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
};

const getStatusCopy = (analytics: AnalyticsData | null) => {
  const freshness = analytics?.freshness;
  if (!freshness) return "Freshness data unavailable.";
  if (freshness.stalenessAlert) {
    return `Only ${freshness.recent7DayCount} updates in the last 7 days. Scraping may be lagging.`;
  }
  return `Fresh data detected: ${freshness.recent7DayCount} updates in the last 7 days.`;
};

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await api.get("/ai/analytics");
        setAnalytics(response.data);
      } catch (err) {
        setError("Failed to load analytics data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  const freshnessCopy = useMemo(() => getStatusCopy(analytics), [analytics]);

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin text-4xl mb-4">⏳</div>
            <p className="text-[#888]">Loading analytics...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex items-center gap-4 mb-8">
            <Link href="/dashboard" className="text-[#00d9ff] hover:text-[#7f5af0] transition">
              ← Back
            </Link>
            <h1 className="text-3xl font-bold text-white">Analytics</h1>
          </div>
          <div className="card p-6 border border-red-500/50 bg-red-500/10">
            <p className="text-red-300">{error}</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/dashboard" className="text-[#00d9ff] hover:text-[#7f5af0] transition">
            ← Back
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-white">Analytics Overview</h1>
            <p className="text-sm text-[#888] mt-1">
              A plain-language view of usage, content freshness, and AI behavior.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          <div className="card p-6 border border-white/10">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Queries answered</p>
            <p className="mt-2 text-3xl font-bold text-[#00d9ff]">{analytics?.totalQueries || 0}</p>
            <p className="text-xs text-[#666] mt-2">Total user questions processed.</p>
          </div>
          <div className="card p-6 border border-white/10">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Alerts active</p>
            <p className="mt-2 text-3xl font-bold text-[#7f5af0]">{analytics?.totalAlerts || 0}</p>
            <p className="text-xs text-[#666] mt-2">Saved or configured notifications.</p>
          </div>
          <div className="card p-6 border border-white/10">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">AI usage</p>
            <p className="mt-2 text-3xl font-bold text-[#aaff00]">{analytics?.aiUsageCount || 0}</p>
            <p className="text-xs text-[#666] mt-2">Updates available for analysis.</p>
          </div>
          <div className="card p-6 border border-white/10">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Avg response</p>
            <p className="mt-2 text-3xl font-bold text-[#00d9ff]">{analytics?.averageResponseTime || 0}s</p>
            <p className="text-xs text-[#666] mt-2">Typical AI response time.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1.3fr_0.7fr] gap-6">
          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4">What this data means</h2>
            <div className="space-y-3 text-sm text-[#d7d7d7] leading-relaxed">
              <p>{freshnessCopy}</p>
              <p>
                The dashboard now emphasizes newest updates first, so if March 21 or March 22 items exist in the database,
                they should be visible unless the source itself has not published them yet.
              </p>
              <p>
                If the freshness panel shows few updates in the last 7 days, scraping is either lagging or the sources were quiet.
              </p>
            </div>
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Latest update</p>
                <p className="mt-2 text-white font-semibold">{formatDate(analytics?.freshness?.latestUpdateDate)}</p>
                <p className="mt-2 text-xs text-[#666]">{analytics?.freshness?.latestUpdateTitle || "No update title available"}</p>
              </div>
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Last 7 days</p>
                <p className="mt-2 text-white font-semibold">{analytics?.freshness?.recent7DayCount || 0} updates</p>
                <p className="mt-2 text-xs text-[#666]">Used to spot stale scraping.</p>
              </div>
            </div>
          </div>

          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4">Data freshness check</h2>
            <div className={`rounded-2xl p-4 border ${analytics?.freshness?.stalenessAlert ? "border-amber-500/40 bg-amber-500/10" : "border-green-500/30 bg-green-500/10"}`}>
              <p className="text-sm text-white font-medium">
                {analytics?.freshness?.stalenessAlert ? "Possible scrape lag" : "Scrape looks current"}
              </p>
              <p className="mt-2 text-xs text-[#ccc]">
                Latest record: {formatDate(analytics?.freshness?.latestUpdateDate)}
              </p>
            </div>
            <div className="mt-4 space-y-2 text-sm text-[#d7d7d7]">
              <div className="flex justify-between gap-3">
                <span>Recent 7-day updates</span>
                <span className="text-[#00d9ff] font-semibold">{analytics?.freshness?.recent7DayCount || 0}</span>
              </div>
              <div className="flex justify-between gap-3">
                <span>Newest published record</span>
                <span className="text-[#00d9ff] font-semibold">{formatDate(analytics?.freshness?.latestUpdateDate)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4">Authority coverage</h2>
            <div className="space-y-4">
              {analytics?.authorityActivity?.map((item, i) => {
                const maxCount = Math.max(...(analytics?.authorityActivity?.map((a) => a.count) || [1]));
                const percentage = Math.max(8, (item.count / maxCount) * 100);
                return (
                  <div key={i} className="rounded-2xl bg-white/5 border border-white/10 p-3">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <div>
                        <p className="text-sm font-semibold text-white">{item.authority}</p>
                        <p className="text-xs text-[#888]">
                          Latest: {formatDate(item.latestUpdate)}
                        </p>
                      </div>
                      <span className="text-sm text-[#00d9ff] font-bold">{item.count} updates</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
                      <div
                        className="h-3 rounded-full bg-gradient-to-r from-[#00d9ff] to-[#7f5af0] transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4">AI behavior summary</h2>
            <div className="space-y-4">
              {analytics?.queryClassification?.map((item, i) => {
                const colorMap: Record<string, string> = {
                  "General Knowledge": "#00d9ff",
                  "Database Search": "#7f5af0",
                  "Fallback": "#ff6b6b",
                };
                const color = colorMap[item.type] || "#888";
                return (
                  <div key={i} className="rounded-2xl bg-white/5 border border-white/10 p-3">
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <span className="text-sm font-semibold text-white">{item.type}</span>
                      <div className="text-right">
                        <p className="text-sm font-bold" style={{ color }}>{item.percentage}%</p>
                        <p className="text-xs text-[#888]">{item.count} queries</p>
                      </div>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
                      <div className="h-3 rounded-full" style={{ width: `${item.percentage}%`, background: color }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold text-white mb-4">Weekly trend</h2>
          <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
            {analytics?.weeklyTrend?.map((item, i) => {
              const maxQueries = Math.max(...(analytics?.weeklyTrend?.map((d) => d.queries) || [1]));
              const percentage = Math.max(10, (item.queries / maxQueries) * 100);
              return (
                <div key={i} className="rounded-2xl bg-white/5 border border-white/10 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#888]">{item.day}</p>
                  <div className="mt-3 h-24 flex items-end">
                    <div
                      className="w-full rounded-t-xl bg-gradient-to-t from-[#00d9ff] to-[#7f5af0]"
                      style={{ height: `${percentage}%` }}
                    />
                  </div>
                  <p className="mt-3 text-sm font-semibold text-white">{item.queries} queries</p>
                  <p className="text-xs text-[#888]">{item.date}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Layout>
  );
}