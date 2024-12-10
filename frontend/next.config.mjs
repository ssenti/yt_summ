/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*'
        }
      ]
    }
    return []
  },
  // Disable image optimization in development
  images: {
    unoptimized: process.env.NODE_ENV === 'development'
  }
}

export default nextConfig
