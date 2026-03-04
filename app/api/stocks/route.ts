import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const skip = searchParams.get("skip") || "0";
    const limit = searchParams.get("limit") || "50";
    const q = searchParams.get("q");
    const sector = searchParams.get("sector");

    let url: string;
    if (q) {
      url = `${API_BASE}/api/stocks/search?q=${encodeURIComponent(q)}&skip=${skip}&limit=${limit}`;
    } else {
      const params = new URLSearchParams();
      params.set("skip", skip);
      params.set("limit", limit);
      if (sector) {
        params.set("sector", sector);
      }
      url = `${API_BASE}/api/stocks/stocks?${params.toString()}`;
    }

    const res = await fetch(url, { cache: "no-store" });
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: "Failed to fetch stocks" }, { status: 500 });
  }
}
