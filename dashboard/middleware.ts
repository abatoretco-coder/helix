import { NextRequest, NextResponse } from "next/server";

const AUTH_ENABLED = process.env.DASHBOARD_BASIC_AUTH_ENABLED === "true";
const AUTH_USER = process.env.DASHBOARD_BASIC_AUTH_USER || "";
const AUTH_PASSWORD = process.env.DASHBOARD_BASIC_AUTH_PASSWORD || "";

function unauthorized() {
  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Helix Dashboard"',
    },
  });
}

function decodeCredentials(header: string): { user: string; password: string } | null {
  if (!header.startsWith("Basic ")) {
    return null;
  }

  try {
    const decoded = atob(header.slice("Basic ".length));
    const separator = decoded.indexOf(":");
    if (separator < 0) {
      return null;
    }
    return {
      user: decoded.slice(0, separator),
      password: decoded.slice(separator + 1),
    };
  } catch {
    return null;
  }
}

export function middleware(request: NextRequest) {
  if (!AUTH_ENABLED || !AUTH_USER || !AUTH_PASSWORD) {
    return NextResponse.next();
  }

  const credentials = decodeCredentials(request.headers.get("authorization") || "");
  if (!credentials || credentials.user !== AUTH_USER || credentials.password !== AUTH_PASSWORD) {
    return unauthorized();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
