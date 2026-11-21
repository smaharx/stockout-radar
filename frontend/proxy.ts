import { NextResponse } from "next/server";

export function proxy() {
  // Public dashboard: no frontend Basic Authentication required.
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};