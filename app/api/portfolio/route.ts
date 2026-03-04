import { NextResponse } from "next/server";

const API_BASE = "http://localhost:8000";

export async function GET() {
  try {
    const res = await fetch(`${API_BASE}/api/portfolio/portfolio`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch portfolio" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const res = await fetch(`${API_BASE}/api/portfolio/portfolio`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to create portfolio" }, { status: 500 });
  }
}
