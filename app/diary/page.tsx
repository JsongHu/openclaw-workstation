"use client";

import { useEffect, useState } from "react";

interface AgentDiary {
  agent: string;
  name: string;
  icon: string;
  latestDate: string;
  summary: string;
  path: string;
}

const AGENT_INFO: Record<string, { name: string; icon: string }> = {
  main: { name: "小狗", icon: "🐶" },
  finance: { name: "小猫", icon: "🐱" },
  social: { name: "小驴", icon: "🫏" },
};

export default function DiaryPage() {
  const [agents, setAgents] = useState<AgentDiary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDiaryAgents();
  }, []);

  const fetchDiaryAgents = async () => {
    try {
      const res = await fetch("/api/diary-agents");
      if (res.ok) {
        const data = await res.json();
        
        const diaryAgents: AgentDiary[] = data.map((item: any) => ({
          agent: item.agent,
          name: AGENT_INFO[item.agent]?.name || item.agent,
          icon: AGENT_INFO[item.agent]?.icon || "🤖",
          latestDate: new Date().toISOString().split("T")[0],
          summary: `${item.diary_count} 篇日记`,
          path: `/diary/${item.agent}`,
        }));
        
        setAgents(diaryAgents);
      }
    } catch (e) {
      console.error("获取日记失败:", e);
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
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">📔 工作日记</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((item) => (
          <a
            key={item.agent}
            href={item.path}
            className="block p-6 bg-[var(--card)] border border-[var(--border)] rounded-lg hover:border-[var(--accent)] hover:shadow-lg transition-all duration-200"
          >
            <div className="flex items-center gap-3 mb-3">
              <span className="text-3xl">{item.icon}</span>
              <div>
                <h2 className="text-lg font-semibold text-[var(--text)]">{item.name}</h2>
                <p className="text-sm text-[var(--text-muted)]">Agent: {item.agent}</p>
              </div>
            </div>
            <div className="text-sm text-[var(--text-muted)] mb-2">
              📅 最新: {item.latestDate}
            </div>
            <p className="text-sm text-[var(--text-muted)] line-clamp-2">
              {item.summary}
            </p>
          </a>
        ))}
      </div>

      {agents.length === 0 && (
        <div className="text-center text-gray-500 py-12">
          暂无日记记录
        </div>
      )}
    </div>
  );
}
