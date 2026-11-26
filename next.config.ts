import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // Emit `path/index.html` so S3+CloudFront can serve directory URLs directly.
  // Requests to `/path` (no trailing slash) must be redirected to `/path/`
  // at the CloudFront layer (viewer-request function) or they will 404/403.
  trailingSlash: true,
  productionBrowserSourceMaps: false,
};

export default nextConfig;
