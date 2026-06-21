/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${process.env.BACKEND_URL || 'http://127.0.0.1:8787'}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
