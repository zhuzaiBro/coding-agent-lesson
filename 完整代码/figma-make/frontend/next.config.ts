import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production" || process.env.VERCEL === "1";
const PROD_API_BASE_URL = "https://coding-agent.zood.work";
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  (isProd ? PROD_API_BASE_URL : "http://localhost:7001");

const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: API_BASE_URL,
  },
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8001",
        pathname: "/images/**",
      },
      {
        protocol: "https",
        hostname: "coding-agent.zood.work",
        pathname: "/**",
      },
    ],
  },
  async rewrites() {
    // 生产/Vercel 走 NEXT_PUBLIC_API_BASE_URL，仅本地 dev 代理到 7001
    if (isProd) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:7001/api/:path*",
      },
    ];
  },
};

export default nextConfig;
