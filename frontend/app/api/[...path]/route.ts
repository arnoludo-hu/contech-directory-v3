
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const base = (
  process.env.FASTAPI_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const sleep = (ms: number) =>
  new Promise<void>(resolve => setTimeout(resolve, ms));

async function waitForBackend(): Promise<boolean> {
  // Bounded readiness polling for Render cold starts.
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const response = await fetch(`${base}/health`, {
        cache: "no-store",
        signal: AbortSignal.timeout(20000)
      });

      if (response.ok) return true;
    } catch {
      // Backend may still be starting.
    }

    if (attempt < 3) await sleep(3000);
  }

  return false;
}

async function forward(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> }
) {
  const { path } = await ctx.params;

  if (path.some(p => p === "..")) {
    return NextResponse.json(
      { detail: "Invalid path" },
      { status: 400 }
    );
  }

  const pathname = "/api/" + path.join("/");
  const url = base + pathname + req.nextUrl.search;

  const headers: Record<string, string> = {
    "Content-Type":
      req.headers.get("content-type") || "application/json"
  };

  // Preserve existing admin access check.
  if (path[1] === "admin") {
    const token = req.headers.get("x-admin-key");

    if (
      !process.env.ADMIN_API_KEY ||
      !token ||
      token !== process.env.ADMIN_API_KEY
    ) {
      return NextResponse.json(
        { detail: "Admin authentication required" },
        { status: 401 }
      );
    }

    headers["x-admin-key"] = process.env.ADMIN_API_KEY;
  }

  // Check backend readiness before forwarding.
  const ready = await waitForBackend();

  if (!ready) {
    return NextResponse.json(
      {
        detail:
          "Search service is starting. Please try again shortly."
      },
      { status: 503 }
    );
  }

  try {
    const response = await fetch(url, {
      method: req.method,
      headers,
      body: ["GET", "HEAD"].includes(req.method)
        ? undefined
        : await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(60000)
    });

    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") ||
          "application/json"
      }
    });

  } catch (error) {
    console.error("FastAPI proxy request failed:", error);

    return NextResponse.json(
      {
        detail:
          "Search service temporarily unavailable. Please retry."
      },
      { status: 503 }
    );
  }
}

export {
  forward as GET,
  forward as POST,
  forward as PATCH,
  forward as DELETE
};
