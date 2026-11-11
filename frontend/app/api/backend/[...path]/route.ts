import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const configuredBackendOrigin = process.env.STOCKOUT_RADAR_API_URL?.trim();

  if (process.env.NODE_ENV === "production" && !configuredBackendOrigin) {
    return Response.json(
      { detail: "The backend service URL is not configured." },
      { status: 503 },
    );
  }

  const backendOrigin = (
    configuredBackendOrigin ?? "http://127.0.0.1:8001"
  ).replace(/\/$/, "");
  const endpoint = `${backendOrigin}/api/${path.map(encodeURIComponent).join("/")}`;
  const backendApiKey = process.env.STOCKOUT_RADAR_API_KEY;

  if (process.env.NODE_ENV === "production" && !backendApiKey) {
    return Response.json(
      { detail: "Backend API authentication is not configured." },
      { status: 503 },
    );
  }
  const target = new URL(endpoint);
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.append(key, value);
  });

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers: {
        Accept: "application/json",
        ...(backendApiKey
          ? { Authorization: `Bearer ${backendApiKey}` }
          : {}),
        ...(request.headers.get("content-type")
          ? { "Content-Type": request.headers.get("content-type") as string }
          : {}),
      },
      body: request.method === "GET" || request.method === "HEAD"
        ? undefined
        : await request.arrayBuffer(),
      cache: "no-store",
    });

    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("content-type") ?? "application/json",
        "Cache-Control": "no-store, max-age=0",
      },
    });
  } catch {
    return Response.json(
      {
        detail:
          "The backend service is unavailable. Check STOCKOUT_RADAR_API_URL and confirm the FastAPI server is running.",
      },
      { status: 502 },
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
