import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET(request: Request, { params }: { params: Promise<{ owner: string }> }) {
  try {
    const { owner } = await params;
    const res = await fetch(`${API_BASE}/api/portfolio/account/${owner}/balance`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch balance" }, { status: 500 });
  }
}
