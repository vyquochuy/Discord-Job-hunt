/**
 * Job Hunter Platform — Runtime Environment Configuration
 *
 * File này được phục vụ tại /env.js trên cả Vercel (static) và Render (FastAPI route).
 * Vite copy file này từ public/ vào dist/ khi build, giữ nguyên nội dung.
 *
 * - Local dev (localhost / 127.0.0.1): env.ts tự detect, file này bị bỏ qua.
 * - Production (Vercel / Render): file này inject window.ENV để env.ts resolve đúng API_URL.
 */

window.ENV = window.ENV || {
  API_URL: 'https://job-hunt-backend-0hrl.onrender.com',
  ENVIRONMENT: 'production',
};
