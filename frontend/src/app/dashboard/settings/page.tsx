"use client";

import React, { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import Link from "next/link";
import api from "@/lib/api";

interface UserSettings {
  email: string;
  name: string;
  notification_frequency: "daily" | "weekly" | "monthly";
  alert_keywords: string[];
  preferred_authorities: number[];
  digest_enabled: boolean;
  notify_high_risk: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Partial<UserSettings>>({
    notification_frequency: "daily",
    alert_keywords: [],
    preferred_authorities: [],
    digest_enabled: true,
    notify_high_risk: true,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [authorities, setAuthorities] = useState<any[]>([]);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const authRes = await api.get("/authorities/");
        setAuthorities(authRes.data);
        
        // Load user settings from localStorage for now
        const savedSettings = localStorage.getItem("userSettings");
        if (savedSettings) {
          setSettings(JSON.parse(savedSettings));
        }
      } catch (error) {
        console.error("Failed to load settings:", error);
      }
    };
    loadSettings();
  }, []);

  const handleSaveSettings = async () => {
    setLoading(true);
    try {
      localStorage.setItem("userSettings", JSON.stringify(settings));
      setMessage("Settings saved successfully!");
      setTimeout(() => setMessage(""), 3000);
    } catch (error) {
      setMessage("Failed to save settings");
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleAuthorityToggle = (authorityId: number) => {
    const current = settings.preferred_authorities || [];
    if (current.includes(authorityId)) {
      setSettings({
        ...settings,
        preferred_authorities: current.filter((id) => id !== authorityId),
      });
    } else {
      setSettings({
        ...settings,
        preferred_authorities: [...current, authorityId],
      });
    }
  };

  return (
    <Layout>
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link
            href="/dashboard"
            className="text-[#00d9ff] hover:text-[#7f5af0] transition"
          >
            ← Back
          </Link>
          <h1 className="text-3xl font-bold text-white">⚙️ Settings</h1>
        </div>

        {message && (
          <div className={`p-4 rounded-lg ${message.includes("success") ? "bg-green-500/20 text-green-300" : "bg-red-500/20 text-red-300"}`}>
            {message}
          </div>
        )}

        {/* Notification Settings */}
        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold mb-4 text-white">📬 Notification Settings</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Notification Frequency</label>
              <select
                value={settings.notification_frequency || "daily"}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    notification_frequency: e.target.value as any,
                  })
                }
                className="w-full border border-white/10 rounded-lg px-4 py-2.5 bg-white/5 text-white focus:outline-none focus:ring-2 focus:ring-[#00d9ff]"
              >
                <option value="daily">Daily Digest</option>
                <option value="weekly">Weekly Summary</option>
                <option value="monthly">Monthly Report</option>
              </select>
            </div>

            <div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.digest_enabled || false}
                  onChange={(e) =>
                    setSettings({ ...settings, digest_enabled: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-white/20"
                />
                <span className="text-sm font-medium">Enable Email Digest</span>
              </label>
            </div>

            <div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.notify_high_risk || false}
                  onChange={(e) =>
                    setSettings({ ...settings, notify_high_risk: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-white/20"
                />
                <span className="text-sm font-medium">Alert on High-Risk Updates</span>
              </label>
            </div>
          </div>
        </div>

        {/* Authority Preferences */}
        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold mb-4 text-white">🌍 Authority Preferences</h2>
          <p className="text-sm text-[#888] mb-4">Select which regulatory authorities to monitor</p>
          <div className="grid grid-cols-2 gap-3">
            {authorities.map((authority) => (
              <label key={authority.id} className="flex items-center gap-3 cursor-pointer p-3 rounded-lg hover:bg-white/5 transition">
                <input
                  type="checkbox"
                  checked={(settings.preferred_authorities || []).includes(authority.id)}
                  onChange={() => handleAuthorityToggle(authority.id)}
                  className="w-4 h-4 rounded border-white/20"
                />
                <span className="text-sm font-medium">{authority.name}</span>
                <span className="text-xs text-[#666]">({authority.country})</span>
              </label>
            ))}
          </div>
        </div>

        {/* Alert Keywords */}
        <div className="card p-6 border border-white/10">
          <h2 className="text-xl font-semibold mb-4 text-white">🔑 Alert Keywords</h2>
          <p className="text-sm text-[#888] mb-4">Enter keywords to receive alerts. Separate with commas.</p>
          <textarea
            value={(settings.alert_keywords || []).join(", ")}
            onChange={(e) =>
              setSettings({
                ...settings,
                alert_keywords: e.target.value
                  .split(",")
                  .map((k) => k.trim())
                  .filter((k) => k),
              })
            }
            placeholder="e.g., biosimilar, drug safety, adverse events, manufacturing defect"
            className="w-full border border-white/10 rounded-lg px-4 py-3 bg-white/5 text-white placeholder-[#666] focus:outline-none focus:ring-2 focus:ring-[#00d9ff] resize-none h-24"
          />
        </div>

        {/* Save Button */}
        <div className="flex gap-3">
          <button
            onClick={handleSaveSettings}
            disabled={loading}
            className="flex-1 px-6 py-3 bg-[#00d9ff] text-[#0b152b] font-semibold rounded-lg hover:opacity-90 disabled:opacity-50 transition"
          >
            {loading ? "Saving..." : "💾 Save Settings"}
          </button>
          <Link
            href="/dashboard"
            className="flex-1 px-6 py-3 bg-white/10 text-white font-semibold rounded-lg hover:bg-white/20 transition text-center"
          >
            Cancel
          </Link>
        </div>
      </div>
    </Layout>
  );
}
