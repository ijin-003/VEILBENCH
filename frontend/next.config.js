/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
};

// Vercel uses the standard Next.js output. The standalone server is only for
// the optional self-hosted Docker image.
if (process.env.NEXT_STANDALONE === "true") {
  nextConfig.output = "standalone";
}

module.exports = nextConfig;
