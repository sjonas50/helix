import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // BFF proxy: browser calls /api/proxy/* → Next.js rewrites to FastAPI
  async rewrites() {
    const apiUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/proxy/:path*",
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
