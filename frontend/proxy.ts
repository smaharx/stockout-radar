import { Buffer } from "node:buffer";
import { timingSafeEqual } from "node:crypto";
import { type NextRequest, NextResponse } from "next/server";

function safeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left, "utf8");
  const rightBuffer = Buffer.from(right, "utf8");

  return (
    leftBuffer.length === rightBuffer.length &&
    timingSafeEqual(leftBuffer, rightBuffer)
  );
}

function authenticationRequired(): NextResponse {
  return new NextResponse("Administrator authentication required.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Stockout Radar", charset="UTF-8"',
      "Cache-Control": "no-store",
    },
  });
}

export function proxy(request: NextRequest) {
  // Local development remains unchanged.
  if (process.env.NODE_ENV !== "production") {
    return NextResponse.next();
  }

  const expectedUser = process.env.STOCKOUT_RADAR_ADMIN_USER;
  const expectedPassword = process.env.STOCKOUT_RADAR_ADMIN_PASSWORD;

  if (!expectedUser || !expectedPassword) {
    return new NextResponse(
      "Administrator protection is not configured.",
      { status: 503 },
    );
  }

  const match = request.headers
    .get("authorization")
    ?.match(/^Basic\s+(.+)$/i);

  if (!match) {
    return authenticationRequired();
  }

  let credentials: string;

  try {
    credentials = Buffer.from(match[1], "base64").toString("utf8");
  } catch {
    return authenticationRequired();
  }

  const separator = credentials.indexOf(":");

  if (separator < 0) {
    return authenticationRequired();
  }

  const username = credentials.slice(0, separator);
  const password = credentials.slice(separator + 1);

  if (
    safeEqual(username, expectedUser) &&
    safeEqual(password, expectedPassword)
  ) {
    return NextResponse.next();
  }

  return authenticationRequired();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
