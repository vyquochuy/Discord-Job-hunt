import {
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient, TopRecommendationItem } from '../services/api-client';
import { formatJobLink } from '../utils/formatters';
import { config } from '../config';


export const recommendCommand = {
  data: new SlashCommandBuilder()
    .setName('recommend')
    .setDescription('Xem danh sách các công việc được đề xuất hàng đầu cho hồ sơ của bạn')
    .addIntegerOption((option) =>
      option
        .setName('limit')
        .setDescription('Số lượng việc làm gợi ý (mặc định: 5)')
        .setMinValue(1)
        .setMaxValue(15)
        .setRequired(false)
    )
    .addNumberOption((option) =>
      option
        .setName('min_score')
        .setDescription('Điểm phù hợp tối thiểu (mặc định: 60)')
        .setMinValue(0)
        .setMaxValue(100)
        .setRequired(false)
    ),

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
      await interaction.reply({
        content: '⛔ Bạn không có quyền sử dụng trợ lý cá nhân này.',
        ephemeral: true,
      });
      return;
    }

    await interaction.deferReply({ ephemeral: false });

    const limit = interaction.options.getInteger('limit') || 5;
    const minScore = interaction.options.getNumber('min_score') || 60.0;

    const result = await apiClient.getTopRecommendations(limit, minScore);

    if (!result.success || !result.data) {
      await interaction.editReply({
        content: `❌ **Không thể lấy danh sách đề xuất:** ${result.error}`,
      });
      return;
    }

    const items = result.data;

    if (items.length === 0) {
      const emptyEmbed = new EmbedBuilder()
        .setTitle('🎯 Chưa Có Việc Làm Đề Xuất Phù Hợp')
        .setDescription(
          `Hiện tại chưa có tin tuyển dụng nào đạt điểm $\\ge ${minScore}$ và vượt qua các bộ lọc cứng (Hard Filters).`
        )
        .setColor(0xf39c12)
        .addFields({
          name: '💡 Gợi ý',
          value:
            '• Dùng `/jobs` để duyệt các tin tuyển dụng mới.\n• Thử hạ ngưỡng điểm bằng `/recommend min_score: 40`.\n• Dùng `/profile sync` để cập nhật thêm kỹ năng hoặc dự án mới.',
        });
      await interaction.editReply({ embeds: [emptyEmbed] });
      return;
    }

    const embed = new EmbedBuilder()
      .setTitle(`🌟 Top ${items.length} Việc Làm Phù Hợp Nhất`)
      .setDescription(
        `🌐 **[Mở trên Web Application Dashboard](${config.webAppUrl}/recommendations)**\n` +
        `Danh sách được tính toán tự động dựa trên hồ sơ của bạn (Điểm số $\\ge ${minScore}$ và đủ điều kiện ứng tuyển):`
      )
      .setColor(0x2ecc71);

    items.forEach((item: TopRecommendationItem, index: number) => {
      const scoreBadge = item.score >= 80 ? '🟢' : item.score >= 60 ? '🔵' : '🟡';
      const shortId = item.job_id.split('-')[0];
      const matchedSkills = item.matched_skills.length > 0
        ? item.matched_skills.map((s) => `\`${s}\``).join(' ')
        : '*(Chưa khớp)*';

      const linkText = formatJobLink(item.source_url, item.source);

      embed.addFields({
        name: `${index + 1}. ${scoreBadge} ${item.title} — ${item.company_name} (${item.score.toFixed(1)}/100)`,
        value: `📍 **Địa điểm / Hình thức:** ${item.location || 'N/A'} • \`${item.work_mode}\` • \`${item.level}\`\n🌐 **Link gốc:** ${linkText}\n🛠️ **Kỹ năng đáp ứng:** ${matchedSkills}\n🆔 **Job ID:** \`${item.job_id}\` (Dùng \`/match ${shortId}\` hoặc \`/job ${shortId}\`)`,
        inline: false,
      });

    });

    embed.setFooter({
      text: 'AI Job Hunter • Phase 3 Job Intelligence • Top Recommendations',
    });
    embed.setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  },
};
