import {
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient } from '../services/api-client';

export const data = new SlashCommandBuilder()
  .setName('apply')
  .setDescription('Nộp hồ sơ ứng tuyển (CV + Cover Letter) cho tin tuyển dụng đã chọn')
  .addStringOption((option) =>
    option
      .setName('job_id')
      .setDescription('ID công việc mục tiêu cần nộp hồ sơ')
      .setRequired(true)
  )
  .addStringOption((option) =>
    option
      .setName('recipient_email')
      .setDescription('Địa chỉ email HR nhận hồ sơ (mặc định lấy từ tin tuyển dụng)')
      .setRequired(false)
  )
  .addBooleanOption((option) =>
    option
      .setName('simulate_only')
      .setDescription('Chỉ mô phỏng tạo bản Draft ứng tuyển, không gửi email thật (mặc định: false)')
      .setRequired(false)
  );

export async function execute(interaction: ChatInputCommandInteraction) {
  await interaction.deferReply();

  const jobId = interaction.options.getString('job_id', true).trim();
  const recipientEmail = interaction.options.getString('recipient_email')?.trim();
  const simulateOnly = interaction.options.getBoolean('simulate_only') ?? false;

  const result = await apiClient.submitApplication(jobId, {
    channel: 'EMAIL',
    recipientEmail,
    simulateOnly,
  });

  if (!result.success || !result.data) {
    const errorEmbed = new EmbedBuilder()
      .setColor(0xe74c3c)
      .setTitle('❌ Lỗi Nộp Đơn Ứng Tuyển')
      .setDescription(result.error || 'Không thể thực hiện nộp hồ sơ cho công việc này.')
      .setFooter({ text: 'Job Hunter AI • Phase 4' });

    await interaction.editReply({ embeds: [errorEmbed] });
    return;
  }

  const app = result.data;
  const isSent = app.status === 'SENT';
  const color = isSent ? 0x2ecc71 : 0xf39c12;

  const embed = new EmbedBuilder()
    .setColor(color)
    .setTitle(isSent ? '🚀 Đã Gửi Hồ Sơ Ứng Tuyển Thành Công!' : '📝 Đã Chuẩn Bị Bản Draft Ứng Tuyển')
    .setDescription(
      isSent
        ? `Hồ sơ đã được gửi thành công kèm bản CV PDF và Cover Letter tối ưu.`
        : `Bản Draft ứng tuyển đã được ghi nhận an toàn vào hệ thống.`
    )
    .addFields(
      {
        name: '📨 Kênh & Trạng Thái',
        value: `**Kênh:** \`${app.channel}\`\n**Trạng thái:** \`${app.status}\``,
        inline: true,
      },
      {
        name: '📬 Người Nhận',
        value: `\`${app.recipient_email || 'Chưa xác định'}\``,
        inline: true,
      },
      {
        name: '📋 Tiêu Đề Email',
        value: `\`${app.subject || 'Đơn Ứng Tuyển'}\``,
        inline: false,
      }
    );

  if (app.sent_at) {
    embed.addFields({
      name: '⏰ Thời Gian Gửi',
      value: `<t:${Math.floor(new Date(app.sent_at).getTime() / 1000)}:F>`,
      inline: false,
    });
  }

  embed
    .setFooter({ text: `Application ID: ${app.id}` })
    .setTimestamp();

  await interaction.editReply({ embeds: [embed] });
}

export const applyCommand = { data, execute };

