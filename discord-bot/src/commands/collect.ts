import {
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient } from '../services/api-client';
import { config } from '../config';

export const collectCommand = {
  data: new SlashCommandBuilder()
    .setName('collect')
    .setDescription('Kích hoạt thu thập tin tuyển dụng từ các nguồn việc làm')
    .addStringOption((option) =>
      option
        .setName('source')
        .setDescription('Nguồn việc làm cần thu thập')
        .setRequired(false)
        .addChoices(
          { name: 'Mock Data (Dữ liệu mẫu kiểm thử)', value: 'mock' },
          { name: 'Remotive (Global Remote Tech Jobs)', value: 'remotive' },
          { name: 'ITViec (IT Jobs Vietnam)', value: 'itviec' },
          { name: 'CareerLink (Tech Jobs Vietnam)', value: 'careerlink' },
          { name: 'TopCV (Vietnam Jobs)', value: 'topcv' }
        )
    )
    .addIntegerOption((option) =>
      option
        .setName('limit')
        .setDescription('Số lượng tin tối đa cần thu thập (mặc định: 10, tối đa 50)')
        .setMinValue(1)
        .setMaxValue(50)
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

    const source = interaction.options.getString('source') || 'mock';
    const limit = interaction.options.getInteger('limit') || 5;

    const result = await apiClient.collectJobs(source, limit);

    if (!result.success || !result.data) {
      await interaction.editReply({
        content: `❌ **Thu thập tin tuyển dụng thất bại:** ${result.error}`,
      });
      return;
    }

    const { report } = result.data;

    const embed = new EmbedBuilder()
      .setTitle(`🕷️ Thu Thập Tin Tuyển Dụng Thành Công!`)
      .setDescription(
        `Đã hoàn thành quá trình quét và chuẩn hóa dữ liệu từ nguồn **\`${source.toUpperCase()}\`**:`
      )
      .setColor(0x2ecc71)
      .addFields(
        {
          name: '📥 Tổng số tin quét được',
          value: `\`${report.total_fetched}\``,
          inline: true,
        },
        {
          name: '✨ Tin mới tạo (Created)',
          value: `\`+${report.created}\``,
          inline: true,
        },
        {
          name: '🔄 Tin không đổi (Unchanged)',
          value: `\`${report.unchanged}\``,
          inline: true,
        },
        {
          name: '🛡️ Trùng lặp lọc bỏ (Duplicates)',
          value: `\`${report.duplicates_detected}\``,
          inline: true,
        },
        {
          name: '⚠️ Lỗi bóc tách (Errors)',
          value: `\`${report.errors}\``,
          inline: true,
        }
      )
      .addFields({
        name: '💡 Tiếp theo',
        value:
          '• Dùng `/jobs` để duyệt các tin vừa thu thập.\n• Dùng `/match <id>` để phân tích độ phù hợp với hồ sơ của bạn.\n• Dùng `/recommend` để xem top công việc tốt nhất.',
      })
      .setFooter({
        text: 'AI Job Hunter • Ingestion & Deduplication Pipeline',
      })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  },
};
