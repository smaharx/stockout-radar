import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

const PUBLIC_GET_PATHS = new Set([
  "v1/health",
  "v1/products",
  "v1/forecasts",
  "v1/inventory",
  "v1/inventory/assessment",
]);

const ASSESSMENT_PATH = "v1/inventory/assessment";
const INVENTORY_ITEM_PATTERN = /^v1\/inventory\/[^/]+$/;
const MAX_BODY_BYTES = 16 * 1024;

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const routePath = path.join("/");
  const method = request.method;

  const isKnownReadPath = PUBLIC_GET_PATHS.has(routePath);
  const isAssessmentPath = routePath === ASSESSMENT_PATH;
  const isInventoryItemPath = INVENTORY_ITEM_PATTERN.test(routePath);

  // Allow only the operations required by the public application.
  const allowed =
    (method === "GET" && isKnownReadPath) ||
    (method === "POST" && isAssessmentPath) ||
    (method === "PUT" && isInventoryItemPath);

  if (!allowed) {
    const knownPath =
      isKnownReadPath || isAssessmentPath || isInventoryItemPath;

    const allowedMethods = isKnownReadPath
      ? "GET"
      : isAssessmentPath
        ? "GET, POST"
        : isInventoryItemPath
          ? "PUT"
          : "";

    return Response.json(
      { detail: "This API operation is not available." },
      {
        status: knownPath ? 405 : 404,
        headers: {
          ...(allowedMethods ? { Allow: allowedMethods } : {}),
          "Cache-Control": "no-store",
        },
      },
    );
  }

  const configuredBackendOrigin =
    process.env.STOCKOUT_RADAR_API_URL?.trim();

  if (process.env.NODE_ENV === "production" && !configuredBackendOrigin) {
    return Response.json(
      { detail: "The backend service URL is not configured." },
      { status: 503 },
    );
  }

  const backendOrigin = (
    configuredBackendOrigin ?? "http://127.0.0.1:8001"
  ).replace(/\/$/, "");

  const endpoint = `${backendOrigin}/api/${path
    .map(encodeURIComponent)
    .join("/")}`;

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
    const body =
      method === "GET" ? undefined : await request.arrayBuffer();

    if (body && body.byteLength > MAX_BODY_BYTES) {
      return Response.json(
        { detail: "Request body is too large." },
        { status: 413 },
      );
    }

    const upstream = await fetch(target, {
      method,
      headers: {
        Accept: "application/json",
        ...(backendApiKey
          ? { Authorization: `Bearer ${backendApiKey}` }
          : {}),
        ...(request.headers.get("content-type")
          ? {
              "Content-Type": request.headers.get("content-type")!,
            }
          : {}),
      },
      body,
      cache: "no-store",
    });

    const responseBody = await upstream.text();

    return new Response(responseBody, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") ?? "application/json",
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
