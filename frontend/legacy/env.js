/**
 * Job Hunter Platform — Runtime Environment Configuration
 * 
 * - Môi trường Local (localhost / 127.0.0.1 / file://): Hệ thống tự động nhận diện
 *   và kết nối trực tiếp với backend & database local tại http://localhost:8000/api/v1.
 * - Môi trường Production (Cloudflare Pages, domain public): Hệ thống sử dụng API_URL
 *   để kết nối tới Backend trên Render.
 */

window.ENV = window.ENV || {
  API_URL: 'https://job-hunt-backend-0hrl.onrender.com',
  ENVIRONMENT: 'development',
};

