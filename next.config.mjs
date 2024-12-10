/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable Edge Runtime for API routes
  experimental: {
    runtime: 'edge',
  },
  // Disable image optimization in development
  images: {
    unoptimized: process.env.NODE_ENV === 'development'
  }
}

export default nextConfig
