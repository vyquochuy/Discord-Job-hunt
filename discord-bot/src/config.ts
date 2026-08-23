import dotenv from 'dotenv';
dotenv.config();

export interface BotConfig {
  discordToken: string;
  clientId: string;
  guildId?: string;
  allowedUserId?: string;
  backendApiUrl: string;
  webAppUrl: string;
  internalApiSecret: string;
}

export const config: BotConfig = {
  discordToken: (process.env.DISCORD_TOKEN || '').trim(),
  clientId: (process.env.DISCORD_CLIENT_ID || '').trim(),
  guildId: (process.env.DISCORD_GUILD_ID || '').trim(),
  allowedUserId: (process.env.ALLOWED_USER_ID || '').trim(),
  backendApiUrl: (process.env.BACKEND_API_URL || 'http://localhost:8000').trim(),
  webAppUrl: (process.env.WEB_APP_URL || 'http://localhost:8000').trim(),
  internalApiSecret: (process.env.INTERNAL_API_SECRET || 'change_me_to_a_secure_random_string_32_chars').trim(),
};

// Kiểm tra biến môi trường quan trọng khi khởi chạy
export function validateConfig(): void {
  if (!config.discordToken) {
    console.warn('⚠️ CẢNH BÁO: Chưa cấu hình DISCORD_TOKEN trong file .env');
  }
  if (!config.clientId) {
    console.warn('⚠️ CẢNH BÁO: Chưa cấu hình DISCORD_CLIENT_ID trong file .env');
  }
}
