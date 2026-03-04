import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/funds/funds`, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch funds" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${API_BASE}/api/funds/funds`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error) {
    return NextResponse.json({ error: "Failed to create fund" }, { status: 500 });
  }
}
