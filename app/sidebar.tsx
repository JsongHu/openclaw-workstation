"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n, LanguageSwitcher } from "@/lib/i18n";
import { ThemeSwitcher } from "@/lib/theme";

const NAV_ITEMS = [
  {
    group: "nav.monitor",
    collapsible: true,
    items: [
      { href: "/agents", icon: "🤖", labelKey: "nav.agents" },
      { href: "/models", icon: "🧠", labelKey: "nav.models" },
      { href: "/sessions", icon: "💬", labelKey: "nav.sessions" },
      { href: "/stats", icon: "📊", labelKey: "nav.stats" },
      { href: "/alerts", icon: "🔔", labelKey: "nav.alerts" },
      { href: "/skills", icon: "🧩", labelKey: "nav.skills" },
    ],
  },
  {
    group: "nav.stocks",
    collapsible: true,
    items: [
      { href: "/stocks", icon: "📈", labelKey: "nav.stocks" },
      { href: "/portfolio", icon: "💰", labelKey: "nav.portfolio" },
      { href: "/funds", icon: "🪙", labelKey: "nav.funds" },
      { href: "/stocks/diary", icon: "📔", labelKey: "nav.diary" },
    ],
  },
];

// Pixel Office 作为独立一级菜单（不带分组标题）
const PIXEL_OFFICE_ITEM = { href: "/pixel-office", icon: "🎮", labelKey: "nav.pixelOffice" };

export function Sidebar() {
  const pathname = usePathname();
  const { t } = useI18n();
  const [collapsed, setCollapsed] = useState(false);
  const [stocksCollapsed, setStocksCollapsed] = useState(false);
  const [monitorCollapsed, setMonitorCollapsed] = useState(false);
  const [logoCarry, setLogoCarry] = useState<{ active: boolean; dx: number; dy: number; angle: number; hidden: boolean }>({
    active: false,
    dx: 0,
    dy: 0,
    angle: 0,
    hidden: false,
  });

  useEffect(() => {
    const onStart = () => setLogoCarry((s) => ({ ...s, active: true, hidden: false }));
    const onStop = () => setLogoCarry({ active: false, dx: 0, dy: 0, angle: 0, hidden: false });
    const onProgress = (e: Event) => {
      const ce = e as CustomEvent<{ active: boolean; dx: number; dy: number; angle: number; hidden: boolean }>;
      const d = ce.detail;
      if (!d) return;
      setLogoCarry({ active: !!d.active, dx: d.dx || 0, dy: d.dy || 0, angle: d.angle || 0, hidden: !!d.hidden });
    };
    window.addEventListener("openclaw-logo-drag-start", onStart as EventListener);
    window.addEventListener("openclaw-logo-drag-stop", onStop as EventListener);
    window.addEventListener("openclaw-logo-carry-progress", onProgress as EventListener);
    return () => {
      window.removeEventListener("openclaw-logo-drag-start", onStart as EventListener);
      window.removeEventListener("openclaw-logo-drag-stop", onStop as EventListener);
      window.removeEventListener("openclaw-logo-carry-progress", onProgress as EventListener);
    };
  }, []);

  // 渲染单个菜单项
  const renderNavItem = (item: typeof PIXEL_OFFICE_ITEM, isActive: boolean) => (
    <Link
      key={item.href}
      href={item.href}
      title={collapsed ? t(item.labelKey) : undefined}
      className={`flex items-center rounded-lg text-sm transition-colors ${
        isActive
          ? "bg-[var(--accent)]/15 text-[var(--accent)] font-medium"
          : "text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg)]"
      }`}
      style={{
        padding: collapsed ? "8px 0" : "8px 12px",
        justifyContent: collapsed ? "center" : "flex-start",
        gap: collapsed ? 0 : 10,
      }}
    >
      <span className="text-base">{item.icon}</span>
      {!collapsed && t(item.labelKey)}
    </Link>
  );

  return (
    <>
      <aside
        className="sidebar"
        style={{ width: collapsed ? 64 : 224 }}
      >
        {/* Header: Logo + Toggle */}
        <div className="border-b border-[var(--border)]" style={{ padding: collapsed ? "16px 0" : "16px 20px" }}>
          {collapsed ? (
            <div className="flex flex-col items-center gap-2">
              <Link href="/pixel-office">
                <span
                  className="relative inline-block transition-opacity duration-300"
                  style={{
                    fontSize: "4.219rem",
                    lineHeight: 1,
                    transform: `translate(${logoCarry.dx}px, ${logoCarry.dy}px) rotate(${logoCarry.angle}rad)`,
                    opacity: logoCarry.hidden ? 0 : 1,
                  }}
                >
                  🦞
                </span>
              </Link>
              <button
                onClick={() => setCollapsed(false)}
                className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors text-lg"
                title="展开侧边栏"
              >
                »
              </button>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between">
                <Link href="/pixel-office" className="flex items-center gap-2">
                  <span
                    className="relative inline-block transition-opacity duration-300"
                    style={{
                      fontSize: "4.219rem",
                      lineHeight: 1,
                      transform: `translate(${logoCarry.dx}px, ${logoCarry.dy}px) rotate(${logoCarry.angle}rad)`,
                      opacity: logoCarry.hidden ? 0 : 1,
                    }}
                  >
                    🦞
                  </span>
                  <div>
                    <div className="text-sm font-bold text-[var(--text)] tracking-wide">OPENCLAW</div>
                    <div className="text-[10px] text-[var(--text-muted)] tracking-wider">WORKSTATION</div>
                  </div>
                </Link>
                <button
                  onClick={() => setCollapsed(true)}
                  className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors text-lg"
                  title="收起侧边栏"
                >
                  «
                </button>
              </div>
              <div className="flex items-center gap-2 mt-2 pl-8">
                <LanguageSwitcher />
                <ThemeSwitcher />
              </div>
            </div>
          )}
        </div>

        {/* Nav groups */}
        <nav className="sidebar-nav" style={{ padding: collapsed ? "16px 8px" : "16px 12px" }}>
          <div className="space-y-5">
            {/* 像素办公室 - 独立一级菜单，不带分组标题 */}
            {!collapsed && (
              <div className="space-y-0.5">
                {renderNavItem(PIXEL_OFFICE_ITEM, pathname === PIXEL_OFFICE_ITEM.href)}
              </div>
            )}
            {collapsed && (
              <div className="space-y-0.5">
                {renderNavItem(PIXEL_OFFICE_ITEM, pathname === PIXEL_OFFICE_ITEM.href)}
              </div>
            )}

            {/* 其他分组 */}
            {NAV_ITEMS.map((group) => {
              const isCollapsed =
                (group.group === "nav.stocks" && stocksCollapsed) ||
                (group.group === "nav.monitor" && monitorCollapsed);
              
              return (
              <div key={group.group}>
                {!collapsed && (
                  <div className="px-2 mb-2 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center justify-between">
                    {t(group.group)}
                    {group.collapsible && (
                      <button 
                        onClick={() => {
                          if (group.group === "nav.stocks") setStocksCollapsed(!stocksCollapsed);
                          if (group.group === "nav.monitor") setMonitorCollapsed(!monitorCollapsed);
                        }}
                        className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                        title={isCollapsed ? "展开" : "折叠"}
                      >
                        <span className={`transition-transform ${isCollapsed ? '' : 'rotate-180'}`}>▼</span>
                      </button>
                    )}
                  </div>
                )}
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    // Skip rendering if this item is in a collapsed group
                    if (group.collapsible && isCollapsed) {
                      return null;
                    }
                    const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                    return renderNavItem(item, active);
                  })}
                </div>
              </div>
              );
            })}
          </div>
        </nav>
      </aside>

      {/* Spacer */}
      <div style={{ width: collapsed ? 64 : 224, flexShrink: 0, transition: "width 0.2s" }} />
    </>
  );
}
