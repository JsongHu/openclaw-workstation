"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";

interface Recommendation {
  id: number;
  date: string;
  stock_id: number;
  rank: number;
  score: number;
  signal_count: number;
  signals?: string;
  stock?: { code: string; name: string };
  rsi?: number;
  change_pct?: number;
}

interface StockItem {
  id: number;
  code: string;
  name: string;
  market: string;
  sector?: string;
  price?: number;
  change?: number;
  change_pct?: number;
  volume?: number;
  amount?: number;
  pe?: number;
  pb?: number;
  total_market_cap?: number;
  circulating_market_cap?: number;
  score?: number;
  signal_count?: number;
}

const PAGE_SIZE = 50;

export default function StocksPage() {
  // Top 10 推荐
  const [topStocks, setTopStocks] = useState<Recommendation[]>([]);
  const [topLoading, setTopLoading] = useState(true);

  // 全部股票分页
  const [stocks, setStocks] = useState<StockItem[]>([]);
  const [totalStocks, setTotalStocks] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 筛选条件
  const [filters, setFilters] = useState({
    sector: "",
    minChangePct: "",
    maxChangePct: "",
    minMarketCap: "",
    maxMarketCap: "",
    minPe: "",
    maxPe: "",
  });
  const [filterActive, setFilterActive] = useState(false);

  // 从URL参数初始化筛选状态
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const sector = params.get("sector");
      if (sector) {
        setFilters(prev => ({ ...prev, sector }));
        setFilterActive(true);
        // URL有参数时，手动触发一次数据获取
        setTimeout(() => {
          const skip = (1 - 1) * PAGE_SIZE;
          const url = `/api/stocks?skip=${skip}&limit=${PAGE_SIZE}&sector=${encodeURIComponent(sector)}`;
          fetch(url, { cache: "no-store" })
            .then(r => r.ok ? r.json() : [])
            .then(data => {
              if (Array.isArray(data)) {
                setStocks(data);
                setTotalStocks(data.length);
              }
            });
        }, 100);
      }
    }
  }, []);

  // 获取 Top 10
  const fetchTop = useCallback(() => {
    setTopLoading(true);
    fetch("/api/recommendations/top?limit=10", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setTopStocks(Array.isArray(data) ? data : []))
      .catch(() => setTopStocks([]))
      .finally(() => setTopLoading(false));
  }, []);

  // 搜索
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  // 获取股票列表（分页 or 搜索 or 筛选）
  const fetchStocks = useCallback(() => {
    setLoading(true);
    setError(null);
    const skip = (page - 1) * PAGE_SIZE;

    let url: string;
    if (search) {
      url = `/api/stocks?q=${encodeURIComponent(search)}&skip=${skip}&limit=${PAGE_SIZE}`;
    } else {
      const params = new URLSearchParams();
      params.append("skip", skip.toString());
      params.append("limit", PAGE_SIZE.toString());
      
      // 添加筛选参数
      if (filters.sector) params.append("sector", encodeURIComponent(filters.sector));
      
      url = `/api/stocks?${params.toString()}`;
    }

    fetch(url, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (search) {
          // 搜索返回 { items, total }
          setStocks(Array.isArray(data.items) ? data.items : []);
          setTotalStocks(data.total ?? 0);
        } else {
          // 列表返回数组
          setStocks(Array.isArray(data) ? data : []);
          // 筛选模式下无法获知总数，暂时使用当前返回数量
          if (filterActive) {
            setTotalStocks(data.length || 0);
          }
        }
      })
      .catch(() => {
        setError("无法连接后端服务，请确保 localhost:8000 已启动");
      })
      .finally(() => setLoading(false));
  }, [page, search, filters, filterActive]);

  // 获取总数（仅非搜索模式）
  const fetchCount = useCallback(() => {
    if (search) return;
    fetch("/api/stocks/count", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : { total: 0 }))
      .then((data) => setTotalStocks(data.total ?? 0))
      .catch(() => {});
  }, [search]);

  useEffect(() => {
    fetchTop();
  }, [fetchTop]);

  useEffect(() => {
    fetchStocks();
    if (!search && !filterActive) {
      fetchCount();
    }
  }, [fetchStocks, fetchCount, search, filterActive]);

  // 筛选处理
  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    setFilterActive(true);
    setPage(1);
    // 让 useEffect 触发 fetchStocks
  };

  const clearFilters = () => {
    setFilters({
      sector: "",
      minChangePct: "",
      maxChangePct: "",
      minMarketCap: "",
      maxMarketCap: "",
      minPe: "",
      maxPe: "",
    });
    setFilterActive(false);
    setPage(1);
    // 让 useEffect 触发 fetchStocks
  };

  const totalPages = Math.ceil(totalStocks / PAGE_SIZE);

  const handleSearch = () => {
    setSearch(searchInput.trim());
    setPage(1);
  };

  const handleClearSearch = () => {
    setSearchInput("");
    setSearch("");
    setPage(1);
  };

  // 生成页码按钮
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (page > 3) pages.push("...");
      for (let i = Math.max(2, page - 1); i <= Math.min(totalPages - 1, page + 1); i++) {
        pages.push(i);
      }
      if (page < totalPages - 2) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">股票推荐中心</h1>
        <button
          onClick={() => { fetchTop(); fetchStocks(); fetchCount(); }}
          disabled={loading || topLoading}
          className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg hover:opacity-90 disabled:opacity-50"
        >
          {loading || topLoading ? "刷新中..." : "刷新数据"}
        </button>
      </div>

      {/* ── Top 10 推荐板 ── */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-4">今日 Top 10 推荐</h2>
        {topLoading ? (
          <div className="text-center py-6 text-[var(--text-muted)]">加载推荐中...</div>
        ) : topStocks.length === 0 ? (
          <div className="text-center py-6 text-[var(--text-muted)]">暂无推荐数据</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {topStocks.map((r, i) => (
              <Link
                key={r.id}
                href={`/stocks/${r.stock?.code || ''}`}
                className="relative block p-4 rounded-xl border border-[var(--border)] bg-[var(--card)] hover:border-[var(--accent)] transition-colors cursor-pointer"
              >
                {/* 排名标记 */}
                <div className={`absolute top-2 left-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                  i < 3 ? "bg-amber-500" : "bg-[var(--accent)]"
                }`}>
                  {i + 1}
                </div>

                <div className="mt-4 text-center">
                  <div className="font-mono text-sm text-[var(--text-muted)]">
                    {r.stock?.code || "-"}
                  </div>
                  <div className="font-semibold mt-1 truncate">
                    {r.stock?.name || "-"}
                  </div>
                  <div className="mt-2 flex items-center justify-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      r.score >= 10
                        ? "bg-green-500/20 text-green-400"
                        : "bg-yellow-500/20 text-yellow-400"
                    }`}>
                      {r.score}分
                    </span>
                    <span className="text-xs text-[var(--text-muted)]">
                      {r.signal_count}个信号
                    </span>
                  </div>
                  {r.change_pct != null && (
                    <div className={`mt-1 text-sm font-medium ${
                      r.change_pct >= 0 ? "text-red-500" : "text-green-500"
                    }`}>
                      {r.change_pct >= 0 ? "+" : ""}{r.change_pct.toFixed(2)}%
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* ── 全部股票 ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            全部股票 {totalStocks > 0 && <span className="text-[var(--text-muted)] text-sm font-normal">({totalStocks}只)</span>}
          </h2>
        </div>

        {/* 搜索 */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="搜索股票代码或名称..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="flex-1 px-4 py-2 border border-[var(--border)] rounded-lg bg-[var(--card)] text-[var(--text)]"
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg hover:opacity-90"
          >
            搜索
          </button>
          {search && (
            <button
              onClick={handleClearSearch}
              className="px-4 py-2 border border-[var(--border)] rounded-lg hover:bg-[var(--card)]"
            >
              清除
            </button>
          )}
        </div>

        {/* 筛选条件 */}
        <div className="mb-4 p-4 bg-[var(--card)] rounded-lg border border-[var(--border)]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-medium">筛选条件</h3>
            <div className="flex gap-2">
              <button
                onClick={applyFilters}
                className="px-3 py-1 bg-[var(--accent)] text-white text-sm rounded-lg hover:opacity-90"
              >
                应用筛选
              </button>
              {filterActive && (
                <button
                  onClick={clearFilters}
                  className="px-3 py-1 border border-[var(--border)] text-sm rounded-lg hover:bg-[var(--bg)]"
                >
                  清除筛选
                </button>
              )}
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-[var(--text-muted)] block mb-1">行业板块</label>
              <input
                type="text"
                placeholder="如：银行、电子、医药"
                value={filters.sector}
                onChange={(e) => handleFilterChange("sector", e.target.value)}
                className="w-full px-3 py-1.5 text-sm border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)]"
              />
            </div>
            <div>
              <label className="text-xs text-[var(--text-muted)] block mb-1">筛选状态</label>
              <div className="px-3 py-1.5 text-sm text-[var(--text-muted)]">
                {filterActive ? "✅ 筛选中" : "未筛选"}
              </div>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            {error}
            <button onClick={fetchStocks} className="ml-4 underline">重试</button>
          </div>
        )}

        {loading ? (
          <div className="text-center py-10 text-[var(--text-muted)]">加载中...</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="text-left text-[var(--text-muted)] text-sm border-b border-[var(--border)]">
                    <th className="p-2">序号</th>
                    <th className="p-2">代码</th>
                    <th className="p-2">名称</th>
                    <th className="p-2">行业</th>
                    <th className="p-2">现价</th>
                    <th className="p-2">涨跌幅</th>
                    <th className="p-2">成交量</th>
                    <th className="p-2">总市值</th>
                    <th className="p-2">市盈率</th>
                    <th className="p-2">市净率</th>
                    <th className="p-2">信号数</th>
                  </tr>
                </thead>
                <tbody>
                  {stocks.map((s, idx) => (
                    <tr key={s.id} className="border-b border-[var(--border)] hover:bg-[var(--bg)]">
                      <td className="p-2 text-[var(--text-muted)]">{(page - 1) * PAGE_SIZE + idx + 1}</td>
                      <td className="p-2 font-mono">{s.code}</td>
                      <td className="p-2">
                        <a href={`/stocks/${s.code}`} className="text-[var(--accent)] hover:underline">
                          {s.name || "-"}
                        </a>
                      </td>
                      <td className="p-2 text-[var(--text-muted)]">{s.sector || "-"}</td>
                      <td className="p-2">{s.price ? s.price.toFixed(2) : "-"}</td>
                      <td className="p-2">
                        {s.change_pct != null ? (
                          <span className={s.change_pct >= 0 ? "text-red-500" : "text-green-500"}>
                            {s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(2)}%
                          </span>
                        ) : "-"}
                      </td>
                      <td className="p-2 text-[var(--text-muted)]">
                        {s.volume ? (s.volume / 10000).toFixed(0) + "万" : "-"}
                      </td>
                      <td className="p-2 text-[var(--text-muted)]">
                        {s.total_market_cap ? (s.total_market_cap / 100000000).toFixed(1) + "亿" : "-"}
                      </td>
                      <td className="p-2">{s.pe ? s.pe.toFixed(2) : "-"}</td>
                      <td className="p-2">{s.pb ? s.pb.toFixed(2) : "-"}</td>
                      <td className="p-2">
                        {s.signal_count != null ? (
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                            s.signal_count >= 4
                              ? "bg-green-500/20 text-green-400"
                              : s.signal_count > 0
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "text-[var(--text-muted)]"
                          }`}>
                            {s.signal_count}
                          </span>
                        ) : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {stocks.length === 0 && !error && (
                <div className="text-center py-10 text-[var(--text-muted)]">
                  {search ? "未找到匹配的股票" : "暂无数据"}
                </div>
              )}
            </div>

            {/* 分页 */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4 text-sm">
                <div className="text-[var(--text-muted)]">
                  第 {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, totalStocks)} 条，共 {totalStocks} 条
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(Math.max(1, page - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 rounded border border-[var(--border)] hover:bg-[var(--card)] disabled:opacity-30"
                  >
                    上一页
                  </button>
                  {getPageNumbers().map((p, i) =>
                    p === "..." ? (
                      <span key={`ellipsis-${i}`} className="px-2 text-[var(--text-muted)]">...</span>
                    ) : (
                      <button
                        key={p}
                        onClick={() => setPage(p as number)}
                        className={`px-3 py-1 rounded border ${
                          page === p
                            ? "bg-[var(--accent)] text-white border-[var(--accent)]"
                            : "border-[var(--border)] hover:bg-[var(--card)]"
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}
                  <button
                    onClick={() => setPage(Math.min(totalPages, page + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 rounded border border-[var(--border)] hover:bg-[var(--card)] disabled:opacity-30"
                  >
                    下一页
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
