import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const API_BASE = "http://localhost:8000";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get("limit") || "50";
    const res = await fetch(
      `${API_BASE}/api/recommendations/recommendations?limit=${limit}`,
      { cache: "no-store" }
    );
    if (!res.ok) {
      return NextResponse.json([], { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json([], { status: 502 });
  }
}
