"use client";
import React, { useState } from "react";
import Layout from "@/components/Layout";
import api from "@/lib/api";

type SourceItem = {
    id: number;
    title: string;
    source_link: string;
    published_date: string;
    authority_id: number;
};

const suggestedQueries = [
    "What are the latest FDA guidelines on biosimilars?",
    "Which regulatory updates in the last 30 days affect medical devices?",
    "What are the key takeaways from recent EMA guidance?",
    "Show me drug safety updates from all authorities",
];

export default function ChatPage() {
    const [query, setQuery] = useState("");
    const [messages, setMessages] = useState<
        { role: "user" | "assistant"; content: string; sources?: SourceItem[] }[]
    >([]);
    const [loading, setLoading] = useState(false);

    const handleSend = async (text?: string) => {
        const messageText = text || query;
        if (!messageText.trim()) return;

        console.log("=".repeat(80));
        console.log("[FRONTEND] Sending query:", messageText);
        console.log("=".repeat(80));

        setMessages((prevMessages) => [...prevMessages, { role: "user", content: messageText }]);
        setQuery("");
        setLoading(true);

        try {
            const res = await api.post("/ai/query", { query: messageText });
            console.log("[FRONTEND] Received response:", res.data);
            console.log("[FRONTEND] Answer preview:", res.data.answer.substring(0, 100) + "...");
            console.log("[FRONTEND] Sources count:", res.data.sources?.length || 0);
            console.log("=".repeat(80));
            
            setMessages((prevMessages) => [
                ...prevMessages,
                { role: "assistant", content: res.data.answer, sources: res.data.sources || [] },
            ]);
        } catch (error) {
            console.error("[FRONTEND] AI query error:", error);
            setMessages((prevMessages) => [
                ...prevMessages,
                { role: "assistant", content: "⚠️ Unable to reach AI service. Please ensure the backend is running on port 8000 and try again." },
            ]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Layout>
            <div className="mx-auto max-w-4xl h-[calc(100vh-160px)] flex flex-col">
                {/* Header */}
                <div className="mb-6">
                    <h1 className="text-3xl font-bold text-[#0b152b] mb-2">💬 Regulatory AI Assistant</h1>
                    <p className="text-[#888]">
                        Query the entire regulatory database. Get AI-powered insights with source citations.
                    </p>
                </div>

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto mb-6 card p-8 border border-white/10 space-y-3">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center py-12">
                            <div className="text-6xl mb-4">🤖</div>
                            <h2 className="text-2xl font-bold text-white mb-2">Ask Anything About Regulations</h2>
                            <p className="text-[#888] mb-8 max-w-md">
                                Get instant answers backed by official regulatory sources and AI analysis.
                            </p>
                            <div className="space-y-2 w-full max-w-md">
                                {suggestedQueries.map((q, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSend(q)}
                                        className="w-full p-3 text-left rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-[#00d9ff]/50 transition text-sm text-[#aaa] hover:text-[#00d9ff]"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>
                        </div>
                    ) : (
                        <>
                            {messages.map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                                    <div className={`max-w-2xl`}>
                                        {msg.role === "user" ? (
                                            <div className="rounded-lg bg-[#00d9ff] text-[#0b152b] px-6 py-3 font-medium">
                                                {msg.content}
                                            </div>
                                        ) : (
                                            <div className="rounded-lg bg-white/10 backdrop-blur border border-white/20 px-6 py-4">
                                                <p className="text-[#0b152b] leading-relaxed font-medium">{msg.content}</p>
                                                {msg.sources && msg.sources.length > 0 && (
                                                    <div className="mt-4 pt-4 border-t border-white/20">
                                                        <p className="text-xs uppercase tracking-[0.2em] text-[#888] font-semibold mb-2">
                                                            📚 Sources ({msg.sources.length})
                                                        </p>
                                                            <div className="space-y-1">
                                                {msg.sources.map((source) => (
                                                    <a
                                                        key={source.id}
                                                        href={source.source_link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="flex flex-col gap-1 p-2 rounded-lg bg-white/10 hover:bg-white/15 transition text-xs text-[#00d9ff] hover:text-[#7f5af0] border border-white/10"
                                                    >
                                                        <span className="font-semibold line-clamp-2">{source.title}</span>
                                                        <span className="text-[#666] text-xs">{new Date(source.published_date).toLocaleDateString()}</span>
                                                    </a>
                                                ))}
                                            </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="flex justify-start">
                                    <div className="rounded-lg bg-white/10 backdrop-blur border border-white/20 px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <div className="w-2 h-2 rounded-full bg-[#00d9ff] animate-bounce" />
                                            <div className="w-2 h-2 rounded-full bg-[#00d9ff] animate-bounce delay-100" />
                                            <div className="w-2 h-2 rounded-full bg-[#00d9ff] animate-bounce delay-200" />
                                            <span className="text-sm text-[#888] ml-2">AI is thinking...</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </>
                    )}
                </div>

                {/* Input Area */}
                <div className="flex gap-3">
                    <input
                        type="text"
                        className="flex-1 border border-white/20 rounded-lg px-4 py-3 bg-white/10 text-[#0b152b] placeholder-[#666] focus:outline-none focus:ring-2 focus:ring-[#00d9ff] focus:border-transparent"
                        placeholder="Ask about regulatory updates, guidelines, or compliance..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyPress={(e) => e.key === "Enter" && !loading && handleSend()}
                    />
                    <button
                        onClick={() => handleSend()}
                        disabled={loading || !query.trim()}
                        className="px-6 py-3 rounded-lg bg-[#00d9ff] text-[#0b152b] font-semibold hover:opacity-90 disabled:opacity-50 transition"
                    >
                        {loading ? "..." : "Send"}
                    </button>
                </div>
            </div>
        </Layout>
    );
}
