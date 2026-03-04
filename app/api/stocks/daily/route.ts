import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
const API_BASE = "http://localhost:8000";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const code = searchParams.get("code");
    const days = searchParams.get("days") || "30";

    if (!code) {
      return NextResponse.json({ error: "Missing code parameter" }, { status: 400 });
    }

    const res = await fetch(
      `${API_BASE}/api/stocks/by-code/${encodeURIComponent(code)}/daily?days=${days}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch daily data" }, { status: 500 });
  }
}
