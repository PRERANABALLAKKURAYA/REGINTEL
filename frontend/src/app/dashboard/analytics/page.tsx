"use client";

import React, { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import Link from "next/link";
import api from "@/lib/api";

interface AnalyticsData {
  totalQueries: number;
  totalAlerts: number;
  aiUsageCount: number;
  averageResponseTime: number;
  authorityActivity: { authority: string; count: number }[];
  categoryDistribution: { category: string; count: number }[];
  weeklyTrend: { day: string; queries: number; date: string }[];
  queryClassification: { type: string; count: number; percentage: number }[];
}

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
            <Link
              href="/dashboard"
              className="text-[#00d9ff] hover:text-[#7f5af0] transition"
            >
              ← Back
            </Link>
            <h1 className="text-3xl font-bold text-white">📊 Analytics</h1>
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
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/dashboard"
            className="text-[#00d9ff] hover:text-[#7f5af0] transition"
          >
            ← Back
          </Link>
          <h1 className="text-3xl font-bold text-white">📊 Analytics Dashboard</h1>
        </div>

        {/* TOP ROW: Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card p-6 border border-white/10 hover:border-[#00d9ff]/30 transition-all">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Total Queries</p>
            <p className="mt-2 text-3xl font-bold text-[#00d9ff]">{analytics?.totalQueries || 0}</p>
            <p className="text-xs text-[#666] mt-2">User queries processed</p>
          </div>

          <div className="card p-6 border border-white/10 hover:border-[#7f5af0]/30 transition-all">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Active Alerts</p>
            <p className="mt-2 text-3xl font-bold text-[#7f5af0]">{analytics?.totalAlerts || 0}</p>
            <p className="text-xs text-[#666] mt-2">Regulatory notifications</p>
          </div>

          <div className="card p-6 border border-white/10 hover:border-[#00d9ff]/30 transition-all">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">AI Usage</p>
            <p className="mt-2 text-3xl font-bold text-[#aaff00]">{analytics?.aiUsageCount || 0}</p>
            <p className="text-xs text-[#666] mt-2">Regulatory updates tracked</p>
          </div>

          <div className="card p-6 border border-white/10 hover:border-[#00d9ff]/30 transition-all">
            <p className="text-xs uppercase tracking-[0.2em] text-[#888]">Avg Response Time</p>
            <p className="mt-2 text-3xl font-bold text-[#00d9ff]">{analytics?.averageResponseTime || 0}s</p>
            <p className="text-xs text-[#666] mt-2">Per AI query</p>
          </div>
        </div>

        {/* MIDDLE SECTION: Authority Activity & Category Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Authority Activity Bar Chart */}
          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              🌍 Authority Activity
            </h2>
            <div className="space-y-4">
              {analytics?.authorityActivity?.map((item, i) => {
                const maxCount = Math.max(...(analytics?.authorityActivity?.map(a => a.count) || [1]));
                const percentage = (item.count / maxCount) * 100;
                return (
                  <div key={i} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white">{item.authority}</span>
                      <span className="text-sm text-[#00d9ff] font-bold">{item.count}</span>
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

          {/* Category Distribution Chart */}
          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              📊 Category Distribution
            </h2>
            <div className="space-y-4">
              {analytics?.categoryDistribution?.map((item, i) => {
                const maxCount = Math.max(...(analytics?.categoryDistribution?.map(c => c.count) || [1]));
                const percentage = (item.count / maxCount) * 100;
                const colors = ['#00d9ff', '#7f5af0', '#aaff00', '#ff6b6b', '#ffd93d'];
                return (
                  <div key={i} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white">{item.category}</span>
                      <span className="text-sm font-bold" style={{ color: colors[i % colors.length] }}>{item.count}</span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
                      <div
                        className="h-3 rounded-full transition-all duration-500"
                        style={{ 
                          width: `${percentage}%`,
                          background: colors[i % colors.length]
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* LOWER SECTION: Weekly Trend & Query Classification */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Weekly Trend Line Chart */}
          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              📈 Weekly Query Trend
            </h2>
            <div className="space-y-4">
              {analytics?.weeklyTrend?.map((item, i) => {
                const maxQueries = Math.max(...(analytics?.weeklyTrend?.map(d => d.queries) || [1]));
                const height = (item.queries / maxQueries) * 100;
                return (
                  <div key={i} className="flex items-end gap-3 h-12">
                    <div className="flex-1 relative">
                      <div className="absolute bottom-0 w-full bg-white/10 rounded-t-lg overflow-hidden" style={{ height: `${height}%` }}>
                        <div className="w-full h-full bg-gradient-to-t from-[#00d9ff] to-[#7f5af0]"></div>
                      </div>
                    </div>
                    <div className="text-xs text-[#888] w-12">{item.day}</div>
                    <div className="text-sm text-[#00d9ff] font-bold w-8 text-right">{item.queries}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* AI Query Classification Chart */}
          <div className="card p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              🤖 AI Query Classification
            </h2>
            <div className="space-y-6">
              {analytics?.queryClassification?.map((item, i) => {
                const colors = {
                  'General Knowledge': '#00d9ff',
                  'Database Search': '#7f5af0',
                  'Fallback': '#ff6b6b'
                };
                const color = colors[item.type as keyof typeof colors] || '#888';
                return (
                  <div key={i} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-white">{item.type}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-[#888]">{item.count} queries</span>
                        <span className="text-sm font-bold" style={{ color }}>{item.percentage}%</span>
                      </div>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
                      <div
                        className="h-3 rounded-full transition-all duration-500"
                        style={{ 
                          width: `${item.percentage}%`,
                          background: color
                        }}
                      />
                    </div>
                  </div>
                );
              })}
              <div className="mt-6 pt-4 border-t border-white/10">
                <p className="text-xs text-[#666] italic">
                  Tracks how the AI system classifies and responds to user queries
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
