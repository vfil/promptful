import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lets the dev server's own assets/HMR load when the page is opened via a
  // LAN IP (e.g. testing on a phone) instead of localhost — otherwise Next.js
  // blocks /_next/* as a cross-origin dev resource. Bare host, no scheme/port.
  // See api/ai-specs/test-localhost-on-phone.md.
  allowedDevOrigins: process.env.DEV_LAN_IP ? [process.env.DEV_LAN_IP] : [],
};

export default nextConfig;
