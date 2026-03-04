"use client";

import { useEffect, useState } from "react";

interface Position {
  id: number;
  stock_code: string;
  stock_name: string;
  shares: number;
  avg_cost: number;
  current_price: number;
  value: number;
  profit: number;
  profit_pct: number;
  stop_loss?: number;
}

interface StockSearchItem {
  id: number;
  code: string;
  name: string;
}

type OwnerType = "小猫" | "松";

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState({
    total_cost: 0,
    total_value: 0,
    total_profit: 0,
    profit_pct: 0,
    balance: 0,
  });
  
  // 持仓人切换
  const [owner, setOwner] = useState<OwnerType>("小猫");
  
  // 添加持仓弹窗
  const [showAddModal, setShowAddModal] = useState(false);
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // 股票搜索
  const [stockSearch, setStockSearch] = useState("");
  const [stockResults, setStockResults] = useState<StockSearchItem[]>([]);
  const [searchingStock, setSearchingStock] = useState(false);
  
  // 表单数据 - 单条模式
  const [formData, setFormData] = useState({
    stock_code: "",
    stock_name: "",
    shares: "",
    avg_cost: "",
  });
  
  // 表单数据 - 批量模式
  const [batchData, setBatchData] = useState<{
    stock_name: string;
    shares: string;
    avg_cost: string;
  }[]>([{ stock_name: "", shares: "", avg_cost: "" }]);

  // 选中的股票（用于显示当前选中的股票信息）
  const [selectedStock, setSelectedStock] = useState<StockSearchItem | null>(null);

  useEffect(() => {
    fetchPortfolio();
  }, [owner]);

  const fetchPortfolio = async () => {
    setError(null);
    setLoading(true);
    try {
      // 根据 owner 参数获取持仓数据
      const res = await fetch(`/api/portfolio/summary?owner=${encodeURIComponent(owner)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      
      // 获取账户余额
      let balance = 0;
      try {
        const balanceRes = await fetch(`/api/portfolio/account/${owner}/balance`);
        if (balanceRes.ok) {
          const balanceData = await balanceRes.json();
          balance = balanceData.balance || 0;
        }
      } catch (e) {
        console.error("获取余额失败:", e);
      }
      
      setPositions(data.positions || []);
      setSummary({
        total_cost: data.total_cost || 0,
        total_value: data.total_value || 0,
        total_profit: data.total_profit || 0,
        profit_pct: data.profit_pct || 0,
        balance: balance,
      });
    } catch (err) {
      setError("无法连接后端，请确保股票分析服务已启动 (localhost:8000)");
    } finally {
      setLoading(false);
    }
  };

  // 搜索股票
  const searchStocks = async (query: string) => {
    if (!query.trim()) {
      setStockResults([]);
      return;
    }
    setSearchingStock(true);
    try {
      const res = await fetch(`/api/stocks?q=${encodeURIComponent(query)}&limit=10`);
      if (res.ok) {
        const data = await res.json();
        const items = data.items || data || [];
        setStockResults(items.slice(0, 10));
      }
    } catch (err) {
      console.error("搜索股票失败:", err);
    } finally {
      setSearchingStock(false);
    }
  };

  // 防抖搜索
  useEffect(() => {
    if (!stockSearch.trim()) {
      setStockResults([]);
      return;
    }
    const timer = setTimeout(() => {
      searchStocks(stockSearch);
    }, 300);
    return () => clearTimeout(timer);
  }, [stockSearch]);

  // 选择股票
  const handleSelectStock = (stock: StockSearchItem) => {
    setSelectedStock(stock);
    setFormData(prev => ({
      ...prev,
      stock_code: stock.code,
      stock_name: stock.name,
    }));
    setStockSearch(stock.name);
    setStockResults([]);
  };

  // 添加单条持仓
  const handleAddPosition = async () => {
    if (!selectedStock || !formData.shares || !formData.avg_cost) {
      alert("请填写完整信息");
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await fetch("/api/portfolio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stock_id: selectedStock.id,
          owner: owner,
          shares: parseInt(formData.shares),
          avg_cost: parseFloat(formData.avg_cost),
        }),
      });
      
      if (res.ok) {
        setShowAddModal(false);
        resetForm();
        fetchPortfolio();
      } else {
        alert("添加失败");
      }
    } catch (err) {
      alert("添加失败: " + err);
    } finally {
      setSubmitting(false);
    }
  };

  // 添加批量持仓
  const handleAddBatch = async () => {
    const validData = batchData.filter(item => 
      item.stock_name && item.shares && item.avg_cost
    );
    
    if (validData.length === 0) {
      alert("请至少填写一条有效的持仓信息");
      return;
    }
    
    setSubmitting(true);
    try {
      // 逐条添加
      for (const item of validData) {
        // 先搜索股票获取ID
        const searchRes = await fetch(`/api/stocks?q=${encodeURIComponent(item.stock_name)}&limit=1`);
        let stockId = 0;
        
        if (searchRes.ok) {
          const searchData = await searchRes.json();
          const items = searchData.items || searchData || [];
          if (items.length > 0) {
            stockId = items[0].id;
          }
        }
        
        if (stockId) {
          await fetch("/api/portfolio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              stock_id: stockId,
              owner: owner,
              shares: parseInt(item.shares),
              avg_cost: parseFloat(item.avg_cost),
            }),
          });
        }
      }
      
      setShowAddModal(false);
      resetForm();
      fetchPortfolio();
    } catch (err) {
      alert("批量添加失败: " + err);
    } finally {
      setSubmitting(false);
    }
  };

  // 重置表单
  const resetForm = () => {
    setFormData({ stock_code: "", stock_name: "", shares: "", avg_cost: "" });
    setBatchData([{ stock_name: "", shares: "", avg_cost: "" }]);
    setStockSearch("");
    setSelectedStock(null);
    setIsBatchMode(false);
  };

  // 批量模式添加行
  const addBatchRow = () => {
    setBatchData([...batchData, { stock_name: "", shares: "", avg_cost: "" }]);
  };

  // 批量模式删除行
  const removeBatchRow = (index: number) => {
    if (batchData.length > 1) {
      setBatchData(batchData.filter((_, i) => i !== index));
    }
  };

  // 更新批量数据
  const updateBatchData = (index: number, field: string, value: string) => {
    const newData = [...batchData];
    newData[index] = { ...newData[index], [field]: value };
    setBatchData(newData);
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">💰 持仓管理</h1>
        <div className="flex items-center gap-3">
          {/* 持仓人切换按钮 */}
          <div className="flex rounded-lg border border-[var(--border)] overflow-hidden">
            <button
              onClick={() => setOwner("小猫")}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                owner === "小猫" 
                  ? "bg-[var(--accent)] text-white" 
                  : "bg-[var(--card)] text-[var(--text)] hover:bg-[var(--bg)]"
              }`}
            >
              🐱 小猫
            </button>
            <button
              onClick={() => setOwner("松")}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                owner === "松" 
                  ? "bg-[var(--accent)] text-white" 
                  : "bg-[var(--card)] text-[var(--text)] hover:bg-[var(--bg)]"
              }`}
            >
              🐿️ 松
            </button>
          </div>
          <button 
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg hover:opacity-90"
          >
            添加持仓
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
          <button onClick={fetchPortfolio} className="ml-4 underline">重试</button>
        </div>
      )}

      {/* 汇总卡片 */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <div className="text-sm text-[var(--text-muted)]">账户余额</div>
          <div className="text-2xl font-bold">¥{summary.balance.toFixed(2)}</div>
        </div>
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <div className="text-sm text-[var(--text-muted)]">总资产</div>
          <div className="text-2xl font-bold">¥{summary.total_value.toFixed(2)}</div>
        </div>
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <div className="text-sm text-[var(--text-muted)]">持仓成本</div>
          <div className="text-2xl font-bold">¥{summary.total_cost.toFixed(2)}</div>
        </div>
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <div className="text-sm text-[var(--text-muted)]">持仓盈亏</div>
          <div
            className={`text-2xl font-bold ${
              summary.total_profit >= 0 ? "text-green-500" : "text-red-500"
            }`}
          >
            {summary.total_profit >= 0 ? "+" : ""}
            {summary.total_profit.toFixed(2)}
          </div>
        </div>
        <div className="p-4 bg-[var(--card)] border border-[var(--border)] rounded-lg">
          <div className="text-sm text-[var(--text-muted)]">盈亏比例</div>
          <div
            className={`text-2xl font-bold ${
              summary.profit_pct >= 0 ? "text-green-500" : "text-red-500"
            }`}
          >
            {summary.profit_pct >= 0 ? "+" : ""}
            {summary.profit_pct.toFixed(2)}%
          </div>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-10 text-[var(--text-muted)]">
          加载中...
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left text-[var(--text-muted)] text-sm border-b border-[var(--border)]">
                <th className="p-3">股票</th>
                <th className="p-3">持仓量</th>
                <th className="p-3">成本价</th>
                <th className="p-3">当前价</th>
                <th className="p-3">市值</th>
                <th className="p-3">盈亏</th>
                <th className="p-3">止损价</th>
                <th className="p-3">操作</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => (
                <tr
                  key={pos.id}
                  className="border-b border-[var(--border)] hover:bg-[var(--bg)]"
                >
                  <td className="p-3">
                    <div className="font-medium">{pos.stock_name}</div>
                    <div className="text-sm text-[var(--text-muted)] font-mono">
                      {pos.stock_code}
                    </div>
                  </td>
                  <td className="p-3">{pos.shares}股</td>
                  <td className="p-3">¥{pos.avg_cost?.toFixed(2)}</td>
                  <td className="p-3">¥{pos.current_price?.toFixed(2)}</td>
                  <td className="p-3">¥{pos.value?.toFixed(2)}</td>
                  <td className="p-3">
                    <div
                      className={
                        pos.profit >= 0 ? "text-green-500" : "text-red-500"
                      }
                    >
                      {pos.profit >= 0 ? "+" : ""}¥{pos.profit?.toFixed(2)}
                    </div>
                    <div
                      className={`text-sm ${
                        pos.profit_pct >= 0 ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      {pos.profit_pct >= 0 ? "+" : ""}
                      {pos.profit_pct?.toFixed(2)}%
                    </div>
                  </td>
                  <td className="p-3">¥{pos.stop_loss?.toFixed(2) || "-"}</td>
                  <td className="p-3">
                    <button className="px-3 py-1 text-sm border border-[var(--border)] rounded hover:bg-[var(--accent)] hover:text-white mr-2">
                      ✏️
                    </button>
                    <button className="px-3 py-1 text-sm border border-[var(--border)] rounded hover:bg-red-500 hover:text-white">
                      🗑️
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {positions.length === 0 && (
            <div className="text-center py-10 text-[var(--text-muted)]">
              暂无持仓
            </div>
          )}
        </div>
      )}

      {/* 添加持仓弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6 border-b border-[var(--border)]">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">添加持仓</h2>
                <button 
                  onClick={() => { setShowAddModal(false); resetForm(); }}
                  className="text-[var(--text-muted)] hover:text-[var(--text)] text-2xl"
                >
                  ×
                </button>
              </div>
              {/* 模式切换 */}
              <div className="flex gap-2 mt-4">
                <button
                  onClick={() => setIsBatchMode(false)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    !isBatchMode 
                      ? "bg-[var(--accent)] text-white" 
                      : "bg-[var(--bg)] text-[var(--text-muted)] hover:bg-[var(--border)]"
                  }`}
                >
                  单条添加
                </button>
                <button
                  onClick={() => setIsBatchMode(true)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isBatchMode 
                      ? "bg-[var(--accent)] text-white" 
                      : "bg-[var(--bg)] text-[var(--text-muted)] hover:bg-[var(--border)]"
                  }`}
                >
                  批量添加
                </button>
              </div>
            </div>

            <div className="p-6">
              {!isBatchMode ? (
                /* 单条添加表单 */
                <div className="space-y-4">
                  {/* 股票搜索 */}
                  <div>
                    <label className="block text-sm font-medium mb-2">股票名称</label>
                    <div className="relative">
                      <input
                        type="text"
                        placeholder="输入股票名称搜索..."
                        value={stockSearch}
                        onChange={(e) => setStockSearch(e.target.value)}
                        className="w-full px-4 py-2 border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)]"
                      />
                      {/* 搜索结果下拉 */}
                      {stockResults.length > 0 && (
                        <div className="absolute z-10 w-full mt-1 bg-[var(--card)] border border-[var(--border)] rounded-lg shadow-lg max-h-60 overflow-y-auto">
                          {stockResults.map((stock) => (
                            <button
                              key={stock.id}
                              onClick={() => handleSelectStock(stock)}
                              className="w-full px-4 py-2 text-left hover:bg-[var(--bg)] flex items-center justify-between"
                            >
                              <span className="font-medium">{stock.name}</span>
                              <span className="text-sm text-[var(--text-muted)] font-mono">{stock.code}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      {searchingStock && (
                        <div className="absolute right-3 top-2 text-sm text-[var(--text-muted)]">
                          搜索中...
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 已选股票信息 */}
                  {selectedStock !== null && selectedStock !== undefined && (
                    <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                      <div className="text-sm text-green-400">✓ 已选择: {selectedStock.name} ({selectedStock.code})</div>
                    </div>
                  )}

                  {/* 持仓股数 */}
                  <div>
                    <label className="block text-sm font-medium mb-2">持仓股数</label>
                    <input
                      type="number"
                      placeholder="输入股数"
                      value={formData.shares}
                      onChange={(e) => setFormData({ ...formData, shares: e.target.value })}
                      className="w-full px-4 py-2 border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)]"
                    />
                  </div>

                  {/* 持仓成本 */}
                  <div>
                    <label className="block text-sm font-medium mb-2">持仓成本 (元/股)</label>
                    <input
                      type="number"
                      step="0.01"
                      placeholder="输入成本价"
                      value={formData.avg_cost}
                      onChange={(e) => setFormData({ ...formData, avg_cost: e.target.value })}
                      className="w-full px-4 py-2 border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)]"
                    />
                  </div>

                  {/* 预览信息 */}
                  {formData.shares && formData.avg_cost && (
                    <div className="p-4 bg-[var(--bg)] rounded-lg">
                      <div className="text-sm text-[var(--text-muted)] mb-2">预览</div>
                      <div className="flex justify-between text-sm">
                        <span>总成本:</span>
                        <span className="font-medium">¥{(parseFloat(formData.shares) * parseFloat(formData.avg_cost)).toFixed(2)}</span>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* 批量添加表单 */
                <div className="space-y-4">
                  <div className="text-sm text-[var(--text-muted)] mb-4">
                    请输入股票名称、股数和成本价，支持一次性添加多条记录
                  </div>
                  
                  {batchData.map((item, index) => (
                    <div key={index} className="flex gap-2 items-start">
                      <div className="flex-1">
                        <input
                          type="text"
                          placeholder="股票名称"
                          value={item.stock_name}
                          onChange={(e) => updateBatchData(index, "stock_name", e.target.value)}
                          className="w-full px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)] text-sm"
                        />
                      </div>
                      <div className="w-24">
                        <input
                          type="number"
                          placeholder="股数"
                          value={item.shares}
                          onChange={(e) => updateBatchData(index, "shares", e.target.value)}
                          className="w-full px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)] text-sm"
                        />
                      </div>
                      <div className="w-28">
                        <input
                          type="number"
                          step="0.01"
                          placeholder="成本价"
                          value={item.avg_cost}
                          onChange={(e) => updateBatchData(index, "avg_cost", e.target.value)}
                          className="w-full px-3 py-2 border border-[var(--border)] rounded-lg bg-[var(--bg)] text-[var(--text)] text-sm"
                        />
                      </div>
                      <button
                        onClick={() => removeBatchRow(index)}
                        disabled={batchData.length === 1}
                        className="px-2 py-2 text-red-500 hover:bg-red-500/10 rounded-lg disabled:opacity-30"
                      >
                        🗑️
                      </button>
                    </div>
                  ))}

                  <button
                    onClick={addBatchRow}
                    className="w-full py-2 border border-dashed border-[var(--border)] rounded-lg text-[var(--text-muted)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors"
                  >
                    + 添加一行
                  </button>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-[var(--border)] flex justify-end gap-3">
              <button
                onClick={() => { setShowAddModal(false); resetForm(); }}
                className="px-4 py-2 border border-[var(--border)] rounded-lg hover:bg-[var(--bg)]"
              >
                取消
              </button>
              <button
                onClick={isBatchMode ? handleAddBatch : handleAddPosition}
                disabled={submitting}
                className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg hover:opacity-90 disabled:opacity-50"
              >
                {submitting ? "提交中..." : "确认添加"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
