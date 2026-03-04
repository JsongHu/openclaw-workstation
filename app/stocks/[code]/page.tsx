"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface DailyData {
  trade_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  amount: number | null;
  change: number | null;
  change_pct: number | null;
}

interface StockInfo {
  id: number;
  code: string;
  name: string;
  market: string;
}

export default function StockDetailPage() {
  const params = useParams();
  const code = params.code as string;

  const [stock, setStock] = useState<StockInfo | null>(null);
  const [daily, setDaily] = useState<DailyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    setError(null);
    fetch(`/api/stocks/daily?code=${encodeURIComponent(code)}&days=30`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setStock(data.stock || null);
        setDaily(Array.isArray(data.daily) ? data.daily : []);
      })
      .catch(() => setError("无法加载数据，请确保后端服务已启动"))
      .finally(() => setLoading(false));
  }, [code]);

  // K线图参数
  const chartWidth = 800;
  const chartHeight = 360;
  const padding = { top: 20, right: 60, bottom: 30, left: 60 };
  const innerW = chartWidth - padding.left - padding.right;
  const innerH = chartHeight - padding.top - padding.bottom;

  // 计算净值曲线（以第一天收盘价为基准 1.0）
  const netValues = daily.map((d, i) => {
    if (!d.close || !daily[0]?.close) return null;
    return d.close / daily[0].close;
  });

  // 计算每日涨跌幅（优先用接口返回值，否则用前后日收盘价计算）
  const changePcts = daily.map((d, i) => {
    if (d.change_pct != null) return d.change_pct;
    if (i === 0 || !d.close || !daily[i - 1]?.close) return null;
    return ((d.close - daily[i - 1].close) / daily[i - 1].close) * 100;
  });

  // 表格用倒序展示（最近日期在最上面），K线图保持正序
  const reversedDaily = [...daily].reverse();
  const reversedNetValues = [...netValues].reverse();
  const reversedChangePcts = [...changePcts].reverse();

  const renderKlineChart = () => {
    if (daily.length === 0) return null;

    const validData = daily.filter((d) => d.open != null && d.close != null && d.high != null && d.low != null);
    if (validData.length === 0) return null;

    const allPrices = validData.flatMap((d) => [d.high!, d.low!]);
    const minPrice = Math.min(...allPrices);
    const maxPrice = Math.max(...allPrices);
    const priceRange = maxPrice - minPrice || 1;
    const pricePad = priceRange * 0.05;

    const yMin = minPrice - pricePad;
    const yMax = maxPrice + pricePad;
    const yRange = yMax - yMin;

    const candleW = Math.max(3, Math.min(12, (innerW / validData.length) * 0.7));
    const gap = innerW / validData.length;

    const toY = (price: number) => padding.top + innerH - ((price - yMin) / yRange) * innerH;
    const toX = (i: number) => padding.left + gap * i + gap / 2;

    // Y轴刻度
    const yTicks = 5;
    const yStep = yRange / yTicks;

    return (
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="w-full" style={{ maxHeight: 400 }}>
        {/* 背景网格 */}
        {Array.from({ length: yTicks + 1 }, (_, i) => {
          const price = yMin + yStep * i;
          const y = toY(price);
          return (
            <g key={`grid-${i}`}>
              <line x1={padding.left} y1={y} x2={chartWidth - padding.right} y2={y}
                stroke="var(--border)" strokeWidth={0.5} strokeDasharray="4,4" />
              <text x={padding.left - 8} y={y + 4} textAnchor="end"
                fill="var(--text-muted)" fontSize={10}>
                {price.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* 蜡烛图 */}
        {validData.map((d, i) => {
          const isUp = d.close! >= d.open!;
          const color = isUp ? "#ef4444" : "#22c55e";
          const bodyTop = toY(Math.max(d.open!, d.close!));
          const bodyBottom = toY(Math.min(d.open!, d.close!));
          const bodyH = Math.max(1, bodyBottom - bodyTop);
          const x = toX(i);

          return (
            <g key={`candle-${i}`}>
              {/* 影线 */}
              <line x1={x} y1={toY(d.high!)} x2={x} y2={toY(d.low!)}
                stroke={color} strokeWidth={1} />
              {/* 实体 */}
              <rect x={x - candleW / 2} y={bodyTop} width={candleW} height={bodyH}
                fill={isUp ? "transparent" : color} stroke={color} strokeWidth={1} />
            </g>
          );
        })}

        {/* X轴日期标签（间隔显示） */}
        {validData.map((d, i) => {
          if (i % Math.max(1, Math.floor(validData.length / 6)) !== 0 && i !== validData.length - 1) return null;
          return (
            <text key={`xlabel-${i}`} x={toX(i)} y={chartHeight - 5}
              textAnchor="middle" fill="var(--text-muted)" fontSize={9}>
              {d.trade_date.slice(5)}
            </text>
          );
        })}
      </svg>
    );
  };

  return (
    <div className="p-6">
      {/* 顶部导航 */}
      <div className="flex items-center gap-4 mb-6">
        <Link href="/stocks"
          className="px-3 py-1.5 border border-[var(--border)] rounded-lg hover:bg-[var(--card)] text-sm">
          &larr; 返回列表
        </Link>
        {stock && (
          <div>
            <h1 className="text-2xl font-bold inline">{stock.name}</h1>
            <span className="ml-3 font-mono text-[var(--text-muted)]">{stock.code}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-16 text-[var(--text-muted)]">加载中...</div>
      ) : daily.length === 0 ? (
        <div className="text-center py-16 text-[var(--text-muted)]">暂无日线数据</div>
      ) : (
        <>
          {/* K线图 */}
          <div className="mb-8 p-4 bg-[var(--card)] rounded-xl border border-[var(--border)]">
            <h2 className="text-lg font-semibold mb-4">近一个月日K线</h2>
            {renderKlineChart()}
          </div>

          {/* 涨跌幅净值曲线 */}
          <div className="mb-8 p-4 bg-[var(--card)] rounded-xl border border-[var(--border)]">
            <h2 className="text-lg font-semibold mb-4">
              涨跌幅净值
              <span className="text-sm font-normal text-[var(--text-muted)] ml-2">
                (以首日收盘价为基准 1.000)
              </span>
            </h2>
            {(() => {
              const valid = netValues.filter((v) => v != null) as number[];
              if (valid.length < 2) return <div className="text-[var(--text-muted)] text-center py-4">数据不足</div>;
              const nvMin = Math.min(...valid) - 0.01;
              const nvMax = Math.max(...valid) + 0.01;
              const nvRange = nvMax - nvMin || 0.01;
              const w = chartWidth;
              const h = 200;
              const gap = innerW / (valid.length - 1);

              const points = valid.map((v, i) => {
                const x = padding.left + gap * i;
                const y = padding.top + (innerH * 0.6) - ((v - nvMin) / nvRange) * (innerH * 0.6);
                return `${x},${y}`;
              }).join(" ");

              const lastNv = valid[valid.length - 1];
              const lineColor = lastNv >= 1.0 ? "#ef4444" : "#22c55e";

              return (
                <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ maxHeight: 220 }}>
                  {/* 基准线 1.0 */}
                  {(() => {
                    const baseY = padding.top + (innerH * 0.6) - ((1.0 - nvMin) / nvRange) * (innerH * 0.6);
                    return (
                      <>
                        <line x1={padding.left} y1={baseY} x2={w - padding.right} y2={baseY}
                          stroke="var(--text-muted)" strokeWidth={0.5} strokeDasharray="6,4" />
                        <text x={padding.left - 8} y={baseY + 4} textAnchor="end"
                          fill="var(--text-muted)" fontSize={10}>1.000</text>
                      </>
                    );
                  })()}
                  <polyline points={points} fill="none" stroke={lineColor} strokeWidth={2} />
                  {/* 终点标注 */}
                  <text x={padding.left + gap * (valid.length - 1) + 8}
                    y={padding.top + (innerH * 0.6) - ((lastNv - nvMin) / nvRange) * (innerH * 0.6) + 4}
                    fill={lineColor} fontSize={11} fontWeight="bold">
                    {lastNv.toFixed(3)}
                  </text>
                </svg>
              );
            })()}
          </div>

          {/* 日线数据表 */}
          <div className="p-4 bg-[var(--card)] rounded-xl border border-[var(--border)]">
            <h2 className="text-lg font-semibold mb-4">日线明细</h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="text-left text-[var(--text-muted)] border-b border-[var(--border)]">
                    <th className="p-2">日期</th>
                    <th className="p-2">开盘</th>
                    <th className="p-2">最高</th>
                    <th className="p-2">最低</th>
                    <th className="p-2">收盘</th>
                    <th className="p-2">涨跌幅</th>
                    <th className="p-2">成交量</th>
                    <th className="p-2">成交额</th>
                    <th className="p-2">净值</th>
                  </tr>
                </thead>
                <tbody>
                  {reversedDaily.map((d, i) => {
                    const nv = reversedNetValues[i];
                    const pct = reversedChangePcts[i];
                    return (
                      <tr key={d.trade_date} className="border-b border-[var(--border)] hover:bg-[var(--bg)]">
                        <td className="p-2 font-mono">{d.trade_date}</td>
                        <td className="p-2">{d.open?.toFixed(2) ?? "-"}</td>
                        <td className="p-2">{d.high?.toFixed(2) ?? "-"}</td>
                        <td className="p-2">{d.low?.toFixed(2) ?? "-"}</td>
                        <td className="p-2 font-medium">{d.close?.toFixed(2) ?? "-"}</td>
                        <td className="p-2">
                          {pct != null ? (
                            <span className={pct >= 0 ? "text-red-500" : "text-green-500"}>
                              {pct >= 0 ? "+" : ""}{pct.toFixed(2)}%
                            </span>
                          ) : "-"}
                        </td>
                        <td className="p-2 text-[var(--text-muted)]">
                          {d.volume ? (d.volume / 10000).toFixed(0) + "万" : "-"}
                        </td>
                        <td className="p-2 text-[var(--text-muted)]">
                          {d.amount ? (d.amount / 10000).toFixed(0) + "万" : "-"}
                        </td>
                        <td className="p-2">
                          {nv != null ? (
                            <span className={nv >= 1.0 ? "text-red-500" : "text-green-500"}>
                              {nv.toFixed(3)}
                            </span>
                          ) : "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
