import { NextResponse } from "next/server";

const API_BASE = "http://localhost:8000";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "10";
    const res = await fetch(`${API_BASE}/api/recommendations/recommendations/top?limit=${limit}`);
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch top recommendations" }, { status: 500 });
  }
}
