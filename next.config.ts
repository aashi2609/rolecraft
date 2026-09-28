import type { NextConfig } from "next";

const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${API_PROXY_TARGET.replace(/\/$/, "")}/:path*`,
      },
    ];
  },
};

export default nextConfig;
