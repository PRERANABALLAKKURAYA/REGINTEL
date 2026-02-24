"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import Layout from "@/components/Layout";

interface UpdateItem {
  id: number;
  title: string;
  category: string;
  published_date: string;
  source_link: string;
  authority_id: number;
  short_summary?: string;
  authority?: {
    id: number;
    name: string;
    country: string;
  };
}

interface AuthorityItem {
  id: number;
  name: string;
  country: string;
}

const categoryChips = [
  "All",
  "Drug Safety",
  "Clinical",
  "Manufacturing",
  "Devices",
  "Quality",
  "Guidance",
  "Notice",
  "Press Announcement",
  "News",
  "Circular",
];

export default function UpdatesPage() {
  const [updates, setUpdates] = useState<UpdateItem[]>([]);
  const [authorities, setAuthorities] = useState<AuthorityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAuthority, setSelectedAuthority] = useState<number | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [page, setPage] = useState(0);
  const itemsPerPage = 15;

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [updatesRes, authoritiesRes] = await Promise.all([
          api.get("/updates/?limit=150"),
          api.get("/authorities/"),
        ]);
        setUpdates(updatesRes.data);
        setAuthorities(authoritiesRes.data);
      } catch (error) {
        console.error("Failed to fetch updates:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const filteredUpdates = useMemo(() => {
    return updates.filter((update) => {
      const matchesSearch = [update.title, update.short_summary]
        .join(" ")
        .toLowerCase()
        .includes(searchTerm.toLowerCase());

      const matchesAuthority = selectedAuthority
        ? update.authority_id === selectedAuthority
        : true;

      const matchesCategory = selectedCategory !== "All"
        ? update.category?.toLowerCase().includes(selectedCategory.toLowerCase())
        : true;

      return matchesSearch && matchesAuthority && matchesCategory;
    });
  }, [updates, searchTerm, selectedAuthority, selectedCategory]);

  const paginatedUpdates = useMemo(() => {
    const start = page * itemsPerPage;
    return filteredUpdates.slice(start, start + itemsPerPage);
  }, [filteredUpdates, page]);

  const totalPages = Math.ceil(filteredUpdates.length / itemsPerPage);

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-screen">
          <p>Loading updates...</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            All Regulatory Updates
          </h1>
          <p className="text-gray-600">
            {filteredUpdates.length} updates found
          </p>
        </div>

        {/* Search and Filters */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          {/* Search Bar */}
          <input
            type="text"
            placeholder="Search updates..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(0);
            }}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-cyan-500"
          />

          {/* Authority Filter */}
          <div className="mb-4">
            <p className="text-sm font-semibold text-gray-700 mb-2">
              Filter by Authority:
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => {
                  setSelectedAuthority(null);
                  setPage(0);
                }}
                className={`px-4 py-1 rounded-full text-sm font-medium transition ${
                  selectedAuthority === null
                    ? "bg-cyan-500 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                All Authorities
              </button>
              {authorities.map((auth) => (
                <button
                  key={auth.id}
                  onClick={() => {
                    setSelectedAuthority(auth.id);
                    setPage(0);
                  }}
                  className={`px-4 py-1 rounded-full text-sm font-medium transition ${
                    selectedAuthority === auth.id
                      ? "bg-cyan-500 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                >
                  {auth.name}
                </button>
              ))}
            </div>
          </div>

          {/* Category Filter */}
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">
              Filter by Category:
            </p>
            <div className="flex flex-wrap gap-2">
              {categoryChips.map((cat) => (
                <button
                  key={cat}
                  onClick={() => {
                    setSelectedCategory(cat);
                    setPage(0);
                  }}
                  className={`px-4 py-1 rounded-full text-sm font-medium transition ${
                    selectedCategory === cat
                      ? "bg-cyan-500 text-white"
                      : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Updates List */}
        <div className="space-y-4">
          {paginatedUpdates.map((update) => (
            <div
              key={update.id}
              className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="px-3 py-1 bg-cyan-100 text-cyan-800 text-xs font-semibold rounded">
                      {update.authority?.name || "Unknown"}
                    </span>
                    <span className="px-3 py-1 bg-gray-100 text-gray-800 text-xs font-semibold rounded">
                      {update.category}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {update.title}
                  </h3>
                  {update.short_summary && (
                    <p className="text-gray-600 text-sm mb-3">
                      {update.short_summary.substring(0, 150)}
                      {update.short_summary.length > 150 ? "..." : ""}
                    </p>
                  )}
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>
                      {new Date(update.published_date).toLocaleDateString()}
                    </span>
                    <a
                      href={update.source_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-600 hover:underline"
                    >
                      View Source →
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex justify-center items-center gap-4 mt-8">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-gray-700">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
              disabled={page === totalPages - 1}
              className="px-4 py-2 bg-cyan-500 text-white rounded-lg disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}

        {/* Back to Dashboard */}
        <div className="mt-8">
          <Link href="/" className="text-cyan-600 hover:underline">
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    </Layout>
  );
}
