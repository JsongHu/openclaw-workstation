import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/portfolio/portfolio/summary`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch portfolio summary" }, { status: 500 });
  }
}
