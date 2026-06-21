import { NextResponse, type NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const appUrl = process.env.APP_URL;
  if (process.env.NODE_ENV !== "production" && appUrl) {
    const canonical = new URL(appUrl);
    const requestHost =
      req.headers.get("x-forwarded-host")?.split(",")[0]?.trim() ??
      req.headers.get("host")?.split(",")[0]?.trim();
    if (
      canonical.hostname === "bowerbird.localhost" &&
      requestHost !== canonical.host
    ) {
      const url = req.nextUrl.clone();
      url.protocol = canonical.protocol;
      url.hostname = canonical.hostname;
      url.port = canonical.port;
      return NextResponse.redirect(url);
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
