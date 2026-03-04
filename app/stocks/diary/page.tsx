"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface DiaryEntry {
  date: string;
  content: string;
  portfolio?: {
    stocks: Array<{
      code: string;
      name: string;
      shares: number;
      avg_cost: number;
    }>;
    totalValue: number;
    cash: number;
  };
}

export default function DiaryPage() {
  const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEntry, setSelectedEntry] = useState<DiaryEntry | null>(null);

  // 加载数据
  useEffect(() => {
    fetchDiaryData();
  }, []);

  const fetchDiaryData = async () => {
    try {
      // 使用前端代理API
      const res = await fetch("/api/diary");
      if (res.ok) {
        const data = await res.json();
        setEntries(data);
      }
    } catch (e) {
      console.error("获取日记失败:", e);
    }
    setLoading(false);
  };

  // 格式化日期显示
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (dateStr === today.toISOString().split("T")[0]) {
      return "今天";
    } else if (dateStr === yesterday.toISOString().split("T")[0]) {
      return "昨天";
    } else {
      return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getFullYear()}`;
    }
  };

  // 获取预览内容（取前100字）
  const getPreview = (content: string) => {
    if (!content) return "无内容";
    return content.length > 80 ? content.substring(0, 80) + "..." : content;
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">📔 理财日记</h1>
        <span className="text-sm text-[var(--text-muted)]">
          共 {entries.length} 篇日记
        </span>
      </div>

      {/* 日记卡片网格 - 会话列表样式 */}
      {entries.length === 0 ? (
        <div className="text-center py-20 text-[var(--text-muted)]">
          <div className="text-4xl mb-4">📔</div>
          <p>暂无日记记录</p>
          <p className="text-sm mt-2">请在后台添加日记数据</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {entries.map((entry, index) => (
            <button
              key={index}
              onClick={() => setSelectedEntry(entry)}
              className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg text-left hover:border-[var(--accent)] hover:shadow-lg transition-all duration-200 group"
            >
              {/* 日期标题 */}
              <div className="flex items-center justify-between mb-2">
                <span className="text-lg font-semibold text-[var(--text)]">
                  {formatDate(entry.date)}
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  {entry.date}
                </span>
              </div>
              
              {/* 预览内容 */}
              <div className="text-sm text-[var(--text-muted)] line-clamp-3 group-hover:text-[var(--text)] transition-colors">
                {getPreview(entry.content)}
              </div>

              {/* 持仓信息 */}
              {entry.portfolio && entry.portfolio.stocks && entry.portfolio.stocks.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[var(--border)]">
                  <div className="text-xs text-[var(--text-muted)]">
                    持仓: {entry.portfolio.stocks.map(s => s.name).join(", ")}
                  </div>
                  <div className="text-xs text-[var(--text-muted)]">
                    市值: ¥{entry.portfolio.totalValue?.toLocaleString() || 0}
                  </div>
                </div>
              )}
            </button>
          ))}
        </div>
      )}

      {/* 日记详情弹窗 */}
      {selectedEntry && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedEntry(null)}
        >
          <div 
            className="bg-[var(--card)] border border-[var(--border)] rounded-xl w-full max-w-3xl max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 弹窗头部 */}
            <div className="p-6 border-b border-[var(--border)] flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">{formatDate(selectedEntry.date)}</h2>
                <div className="text-sm text-[var(--text-muted)]">{selectedEntry.date}</div>
              </div>
              <button 
                onClick={() => setSelectedEntry(null)}
                className="text-[var(--text-muted)] hover:text-[var(--text)] text-2xl"
              >
                ×
              </button>
            </div>

            {/* 弹窗内容 - MD渲染 */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {selectedEntry.content || "*无内容*"}
                </ReactMarkdown>
              </div>

              {/* 持仓信息 */}
              {selectedEntry.portfolio && selectedEntry.portfolio.stocks && selectedEntry.portfolio.stocks.length > 0 && (
                <div className="mt-6 pt-6 border-t border-[var(--border)]">
                  <h3 className="text-lg font-semibold mb-3">💼 当日持仓</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2">股票</th>
                          <th className="text-right py-2">股数</th>
                          <th className="text-right py-2">成本价</th>
                          <th className="text-right py-2">市值</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedEntry.portfolio.stocks.map((stock, i) => (
                          <tr key={i} className="border-b">
                            <td className="py-2">
                              {stock.name}({stock.code})
                            </td>
                            <td className="text-right">{stock.shares}</td>
                            <td className="text-right">¥{stock.avg_cost}</td>
                            <td className="text-right">
                              ¥{(stock.shares * stock.avg_cost).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-3 flex justify-between text-sm">
                    <span className="text-[var(--text-muted)]">
                      现金: ¥{selectedEntry.portfolio.cash?.toLocaleString() || 0}
                    </span>
                    <span className="font-medium">
                      总市值: ¥{selectedEntry.portfolio.totalValue?.toLocaleString() || 0}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
