import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ agent: string }> }
) {
  try {
    const { agent } = await params;
    const targetUrl = `${API_BASE}/api/diary-agents/${agent}`;
    
    const res = await fetch(targetUrl, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch diary" }, { status: 500 });
  }
}
