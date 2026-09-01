/** @type {import('next').NextConfig} */
const apiOrigin = process.env.MODELBRIDGE_API_URL ?? "http://localhost:8010";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
