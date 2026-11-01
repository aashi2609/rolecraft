import type { NextConfig } from "next";

// Validate API_PROXY_TARGET at build time
const API_PROXY_TARGET = process.env.API_PROXY_TARGET;

if (process.env.NODE_ENV === 'production' && !API_PROXY_TARGET) {
  throw new Error(
    'Build failed: API_PROXY_TARGET environment variable is required for production builds'
  );
}

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Content-Security-Policy", value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; frame-ancestors 'none';" },
        ],
      },
    ];
  },
  async rewrites() {
    const target = API_PROXY_TARGET || "http://127.0.0.1:8000";
    return [
      {
        source: "/backend/:path*",
        destination: `${target.replace(/\/$/, "")}/:path*`,
      },
    ];
  },
};

export default nextConfig;
