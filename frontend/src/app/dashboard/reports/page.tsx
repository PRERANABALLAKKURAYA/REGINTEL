"use client";

import React, { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import Link from "next/link";
import api from "@/lib/api";

interface Report {
  id: string;
  title: string;
  generatedAt: string;
  format: "PDF" | "CSV" | "JSON";
  size: string;
  status: "completed" | "processing";
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<"PDF" | "CSV" | "JSON">("CSV");
  const [reportType, setReportType] = useState<"regulatory_updates" | "analytics" | "compliance">("regulatory_updates");

  useEffect(() => {
    // Load stored reports
    const storedReports = localStorage.getItem("generatedReports");
    if (storedReports) {
      setReports(JSON.parse(storedReports));
    }
  }, []);

  const handleGenerateReport = async () => {
    setGeneratingReport(true);
    try {
      const newReport: Report = {
        id: Math.random().toString(36).slice(2),
        title: `${reportType.replace("_", " ").toUpperCase()} Report`,
        generatedAt: new Date().toLocaleString(),
        format: selectedFormat,
        size: "2.4 MB",
        status: "completed",
      };

      let data = "";
      if (reportType === "regulatory_updates") {
        const response = await api.get("/updates");
        if (selectedFormat === "CSV") {
          const updates = response.data;
          const rows: Array<string | number>[] = [
            ["Title", "Authority", "Category", "Published", "Link"],
            ...updates.map((u: any) => [
              u.title,
              u.authority_id,
              u.category,
              new Date(u.published_date).toLocaleDateString(),
              u.source_link,
            ]),
          ];
          const csv = rows
            .map((row: Array<string | number>) =>
              row.map((cell: string | number) => `"${cell}"`).join(",")
            )
            .join("\n");
          data = csv;
        } else if (selectedFormat === "JSON") {
          data = JSON.stringify(response.data, null, 2);
        }
      } else if (reportType === "analytics") {
        data =
          selectedFormat === "JSON"
            ? JSON.stringify(
                {
                  totalQueries: 24,
                  totalAlerts: 5,
                  aiUsage: 42,
                  topCategories: ["Drug Safety", "Manufacturing", "Guidance"],
                },
                null,
                2
              )
            : "Metric,Value\nTotal Queries,24\nActive Alerts,5\nAI Usage,42";
      } else {
        data =
          selectedFormat === "JSON"
            ? JSON.stringify(
                {
                  complianceScore: "92%",
                  issuesFound: 3,
                  criticalAlerts: 0,
                  actionItems: 12,
                },
                null,
                2
              )
            : "Metric,Value\nCompliance Score,92%\nIssues Found,3\nCritical Alerts,0";
      }

      // Download file
      const blob = new Blob([data], {
        type: selectedFormat === "JSON" ? "application/json" : "text/csv",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${newReport.id}.${selectedFormat.toLowerCase()}`;
      a.click();
      URL.revokeObjectURL(url);

      // Add to reports list
      const updatedReports = [newReport, ...reports];
      setReports(updatedReports);
      localStorage.setItem("generatedReports", JSON.stringify(updatedReports));
    } catch (error) {
      console.error("Error generating report:", error);
    } finally {
      setGeneratingReport(false);
    }
  };

  const handleDownload = (report: Report) => {
    // In a real app, this would download from a server
    alert(`Downloading ${report.title}...`);
  };

  const handleDelete = (id: string) => {
    const updatedReports = reports.filter((r) => r.id !== id);
    setReports(updatedReports);
    localStorage.setItem("generatedReports", JSON.stringify(updatedReports));
  };

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
          <h1 className="text-3xl font-bold text-white">📥 Report Generator</h1>
        </div>

        {/* Report Generation Form */}
        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold text-white mb-6">Generate New Report</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-white mb-2">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value as any)}
                className="w-full border border-white/10 rounded-lg px-4 py-2.5 bg-white/5 text-white focus:outline-none focus:ring-2 focus:ring-[#00d9ff]"
              >
                <option value="regulatory_updates">Regulatory Updates</option>
                <option value="analytics">Analytics Summary</option>
                <option value="compliance">Compliance Report</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-white mb-2">File Format</label>
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value as any)}
                className="w-full border border-white/10 rounded-lg px-4 py-2.5 bg-white/5 text-white focus:outline-none focus:ring-2 focus:ring-[#00d9ff]"
              >
                <option value="CSV">CSV</option>
                <option value="JSON">JSON</option>
                <option value="PDF">PDF</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleGenerateReport}
                disabled={generatingReport}
                className="w-full px-6 py-2.5 bg-[#00d9ff] hover:opacity-90 disabled:opacity-50 text-[#0b152b] font-semibold rounded-lg transition"
              >
                {generatingReport ? "Generating..." : "Generate Report"}
              </button>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-[#00d9ff]/10 border border-[#00d9ff]/20">
            <p className="text-sm text-[#00d9ff]">
              Select a report type and format, then click "Generate Report" to create and download your analysis.
            </p>
          </div>
        </div>

        {/* Generated Reports List */}
        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold text-white mb-4">Previously Generated Reports</h2>

          {reports.length === 0 ? (
            <div className="p-6 text-center rounded-lg bg-white/5">
              <p className="text-[#888]">No reports generated yet. Create your first report above.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="p-4 rounded-lg bg-white/5 border border-white/10 hover:border-[#00d9ff]/50 transition"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-semibold text-white">{report.title}</h3>
                      <p className="text-xs text-[#888] mt-1">
                        {report.format} • {report.size} • {report.generatedAt}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-3 py-1 rounded-full font-medium ${
                          report.status === "completed"
                            ? "bg-green-500/20 text-green-300"
                            : "bg-amber-500/20 text-amber-300"
                        }`}
                      >
                        {report.status === "completed" ? "✓ Ready" : "⏳ Processing"}
                      </span>
                      <button
                        onClick={() => handleDownload(report)}
                        className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm font-medium text-[#00d9ff] transition"
                      >
                        Download
                      </button>
                      <button
                        onClick={() => handleDelete(report.id)}
                        className="px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-sm font-medium text-red-300 transition"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Report Templates */}
        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold text-white mb-4">Available Report Types</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <h3 className="font-semibold text-white mb-2">Regulatory Updates</h3>
              <p className="text-sm text-[#888] mb-4">Latest updates from all monitored regulatory authorities with full details.</p>
              <button
                onClick={() => {
                  setReportType("regulatory_updates");
                  handleGenerateReport();
                }}
                className="text-sm text-[#00d9ff] hover:text-[#7f5af0] font-medium"
              >
                Generate →
              </button>
            </div>

            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <h3 className="font-semibold text-white mb-2">Analytics Summary</h3>
              <p className="text-sm text-[#888] mb-4">Comprehensive analytics including query patterns and usage statistics.</p>
              <button
                onClick={() => {
                  setReportType("analytics");
                  handleGenerateReport();
                }}
                className="text-sm text-[#00d9ff] hover:text-[#7f5af0] font-medium"
              >
                Generate →
              </button>
            </div>

            <div className="p-4 rounded-lg bg-white/5 border border-white/10">
              <h3 className="font-semibold text-white mb-2">Compliance Report</h3>
              <p className="text-sm text-[#888] mb-4">Compliance status, open issues, and recommended actions.</p>
              <button
                onClick={() => {
                  setReportType("compliance");
                  handleGenerateReport();
                }}
                className="text-sm text-[#00d9ff] hover:text-[#7f5af0] font-medium"
              >
                Generate →
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
