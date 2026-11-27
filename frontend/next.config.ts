import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  agentRules: false,
  output: "standalone",
  async rewrites() {
    const api = (process.env.API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
    return [{ source: "/api/servidores/:path*", destination: `${api}/api/servidores/:path*` }];
  },
};

export default nextConfig;
