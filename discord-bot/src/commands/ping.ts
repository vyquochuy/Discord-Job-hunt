import { ChatInputCommandInteraction, EmbedBuilder, SlashCommandBuilder } from 'discord.js';
import { apiClient } from '../services/api-client';
import { config } from '../config';

export const pingCommand = {
  data: new SlashCommandBuilder()
    .setName('ping')
    .setDescription('Kiểm tra kết nối và trạng thái của toàn bộ hệ sinh thái Job Hunter Agent'),

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    // 1. Kiểm tra bảo mật: Chỉ cho phép người dùng được cấp quyền thực thi
    if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
      await interaction.reply({
        content: '⛔ Bạn không có quyền sử dụng trợ lý cá nhân này.',
        ephemeral: true,
      });
      return;
    }

    // Defer reply để tránh timeout 3s của Discord
    await interaction.deferReply({ ephemeral: false });

    // 2. Tính toán độ trễ Discord Gateway
    const botPing = interaction.client.ws.ping;

    // 3. Gọi Backend API để lấy trạng thái hệ thống
    const healthResult = await apiClient.getHealth();

    // 4. Tạo Embed thông báo kết quả trực quan
    const isAllHealthy = healthResult.success && healthResult.data?.status === 'healthy';
    const embedColor = isAllHealthy ? 0x2ecc71 : 0xe74c3c; // Xanh lá nếu OK, Đỏ nếu lỗi

    const embed = new EmbedBuilder()
      .setTitle(isAllHealthy ? '🟢 Hệ Thống Hoạt Động Bình Thường' : '🔴 Cảnh Báo Hệ Thống')
      .setDescription('Báo cáo trạng thái kết nối giữa Discord Bot, Backend FastAPI, PostgreSQL và Redis:')
      .setColor(embedColor)
      .addFields(
        {
          name: '📡 Discord Gateway Latency',
          value: `\`${botPing}ms\``,
          inline: true,
        },
        {
          name: '⚡ Backend API Round-trip',
          value: `\`${healthResult.latencyMs}ms\``,
          inline: true,
        },
        {
          name: '⚙️ Environment',
          value: `\`${healthResult.data?.environment || 'unknown'}\``,
          inline: true,
        },
        {
          name: '🧠 FastAPI Backend',
          value: healthResult.success ? '🟢 Online (v' + healthResult.data?.version + ')' : `🔴 Lỗi (${healthResult.error})`,
          inline: false,
        },
        {
          name: '🗄️ PostgreSQL (pgvector)',
          value: healthResult.data?.components?.database === 'connected' ? '🟢 Connected' : '🔴 Disconnected',
          inline: true,
        },
        {
          name: '📋 Redis Task Queue',
          value: healthResult.data?.components?.redis === 'connected' ? '🟢 Connected' : '🔴 Disconnected',
          inline: true,
        }
      )
      .setFooter({ text: 'AI Job Hunter Agent • Phase 0 Foundation' })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  },
};
