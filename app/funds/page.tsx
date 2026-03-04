"use client";

import { useEffect, useState } from "react";

interface Fund {
  id: number;
  fund_code: string;
  fund_name?: string;
  shares: number;
  avg_cost?: number;
  nav?: number;
}

export default function FundsPage() {
  const [funds, setFunds] = useState<Fund[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetchFunds();
  }, []);

  const fetchFunds = async () => {
    setError(null);
    try {
      const res = await fetch("/api/funds");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setFunds(Array.isArray(data) ? data : []);
    } catch (err) {
      setError("无法连接后端，请确保股票分析服务已启动 (localhost:8000)");
    } finally {
      setLoading(false);
    }
  };

  const totalValue = funds.reduce((sum, f) => sum + f.shares * (f.nav || f.avg_cost || 0), 0);
  const totalCost = funds.reduce((sum, f) => sum + f.shares * (f.avg_cost || 0), 0);
  const totalProfit = totalValue - totalCost;
  const profitPct = totalCost > 0 ? (totalProfit / totalCost) * 100 : 0;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">🪙 基金持仓</h1>
        <button
          onClick={fetchFunds}
          className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg hover:opacity-90"
        >
          刷新净值
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
          <button onClick={fetchFunds} className="ml-4 underline">重试</button>
        </div>
      )}

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="p-4 bg-[var(--card)] rounded-lg border border-[var(--border)]">
          <div className="text-sm text-[var(--text-muted)]">总资产</div>
          <div className="text-xl font-bold">¥{totalValue.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="p-4 bg-[var(--card)] rounded-lg border border-[var(--border)]">
          <div className="text-sm text-[var(--text-muted)]">持仓成本</div>
          <div className="text-xl font-bold">¥{totalCost.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</div>
        </div>
        <div className="p-4 bg-[var(--card)] rounded-lg border border-[var(--border)]">
          <div className="text-sm text-[var(--text-muted)]">持仓盈亏</div>
          <div className={`text-xl font-bold ${totalProfit >= 0 ? "text-green-500" : "text-red-500"}`}>
            {totalProfit >= 0 ? "+" : ""}¥{totalProfit.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="p-4 bg-[var(--card)] rounded-lg border border-[var(--border)]">
          <div className="text-sm text-[var(--text-muted)]">盈亏比例</div>
          <div className={`text-xl font-bold ${profitPct >= 0 ? "text-green-500" : "text-red-500"}`}>
            {profitPct >= 0 ? "+" : ""}{profitPct.toFixed(2)}%
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-10 text-[var(--text-muted)]">加载中...</div>
      ) : funds.length === 0 ? (
        <div className="text-center py-10 text-[var(--text-muted)]">暂无基金数据</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left text-[var(--text-muted)] text-sm border-b border-[var(--border)]">
                <th className="p-3">基金代码</th>
                <th className="p-3">基金名称</th>
                <th className="p-3">持有份额</th>
                <th className="p-3">平均成本</th>
                <th className="p-3">最新净值</th>
                <th className="p-3">市值</th>
                <th className="p-3">盈亏</th>
              </tr>
            </thead>
            <tbody>
              {funds.map((fund) => {
                const value = fund.shares * (fund.nav || fund.avg_cost || 0);
                const cost = fund.shares * (fund.avg_cost || 0);
                const profit = value - cost;
                return (
                  <tr key={fund.id} className="border-b border-[var(--border)] hover:bg-[var(--hover)]">
                    <td className="p-3 font-mono">{fund.fund_code}</td>
                    <td className="p-3">{fund.fund_name || "-"}</td>
                    <td className="p-3">{fund.shares.toLocaleString()}</td>
                    <td className="p-3">¥{fund.avg_cost?.toFixed(4) || "-"}</td>
                    <td className="p-3">¥{fund.nav?.toFixed(4) || "-"}</td>
                    <td className="p-3">¥{value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</td>
                    <td className={`p-3 ${profit >= 0 ? "text-green-500" : "text-red-500"}`}>
                      {profit >= 0 ? "+" : ""}¥{profit.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
