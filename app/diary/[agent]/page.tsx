"use client";

import { useEffect, useState, use } from "react";

interface DiaryEntry {
  date: string;
  content: string;
  source?: string;
}

const AGENT_INFO: Record<string, { name: string; icon: string }> = {
  main: { name: "小狗", icon: "🐶" },
  finance: { name: "小猫", icon: "🐱" },
  social: { name: "小驴", icon: "🫏" },
};

export default function AgentDiaryPage({ params }: { params: Promise<{ agent: string }> }) {
  const { agent } = use(params);
  const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const info = AGENT_INFO[agent] || { name: agent, icon: "🤖" };

  useEffect(() => {
    fetchDiaryEntries();
  }, [agent]);

  const fetchDiaryEntries = async () => {
    try {
      const res = await fetch(`/api/diary-agents/${agent}`);
      if (res.ok) {
        const data = await res.json();
        setEntries(data);
      } else {
        setError("获取日记失败");
      }
    } catch (e) {
      setError("获取日记失败");
    }
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <a href="/diary" className="text-blue-500 hover:underline">← 返回</a>
        <span className="text-3xl">{info.icon}</span>
        <h1 className="text-2xl font-bold">{info.name} 的日记</h1>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      <div className="space-y-4">
        {entries.map((entry, i) => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm text-gray-500">{entry.date}</div>
              {entry.source && entry.source !== "root" && (
                <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded">
                  {entry.source}
                </span>
              )}
            </div>
            <div className="whitespace-pre-wrap text-sm">{entry.content}</div>
          </div>
        ))}
      </div>

      {entries.length === 0 && (
        <div className="text-center text-gray-500 py-12">
          暂无日记记录
        </div>
      )}
    </div>
  );
}
