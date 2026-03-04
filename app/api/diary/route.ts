import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/diary/entries`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch diary" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${API_BASE}/api/diary/entries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to save diary" }, { status: 500 });
  }
}
