import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const path = url.pathname.replace("/api/diary-agents", "");
    const targetUrl = `${API_BASE}/api/diary-agents${path}`;
    
    const res = await fetch(targetUrl, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch diary agents" }, { status: 500 });
  }
}
