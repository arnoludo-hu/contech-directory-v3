import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const base = process.env.FASTAPI_BASE_URL;

  if (!base) {
    return NextResponse.json(
      { ready: false, message: "Backend URL not configured" },
      { status: 503 }
    );
  }

  try {
    const response = await fetch(
      `${base.replace(/\/$/, "")}/health`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(75000),
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { ready: false, message: "Backend is starting" },
        { status: 503 }
      );
    }

    return NextResponse.json({ ready: true });
  } catch {
    return NextResponse.json(
      { ready: false, message: "Backend is starting" },
      { status: 503 }
    );
  }
}
