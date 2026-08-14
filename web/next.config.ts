import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      // /opportunities was retired on 2026-08-12: the Layer 2 findings are now the Deep rung of
      // the insight they belong to, rather than a separate catalogue. A published deep-read post
      // links to the old URL, so it redirects to the credit dashboard instead of 404ing.
      { source: "/opportunities", destination: "/", permanent: false },
      { source: "/opportunities/:path*", destination: "/", permanent: false },
    ];
  },
};

export default nextConfig;
