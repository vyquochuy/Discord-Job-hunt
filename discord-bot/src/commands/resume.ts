import {
  AttachmentBuilder,
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient } from '../services/api-client';
import { config } from '../config';

export const data = new SlashCommandBuilder()
  .setName('resume')
  .setDescription('Tự động tạo CV LaTeX chuẩn hóa, build PDF và sinh Cover Letter cho công việc')
  .addStringOption((option) =>
    option
      .setName('job_id')
      .setDescription('ID công việc mục tiêu cần tạo CV')
      .setRequired(true)
  )
  .addBooleanOption((option) =>
    option
      .setName('force_regenerate')
      .setDescription('Bắt buộc sinh lại toàn bộ CV và Cover Letter mới')
      .setRequired(false)
  );

export async function execute(interaction: ChatInputCommandInteraction) {
  await interaction.deferReply();

  const jobId = interaction.options.getString('job_id', true).trim();
  const forceRegenerate = interaction.options.getBoolean('force_regenerate') ?? false;

  const result = await apiClient.tailorResume(jobId, { forceRegenerate });

  if (!result.success || !result.data) {
    const errorEmbed = new EmbedBuilder()
      .setColor(0xe74c3c)
      .setTitle('❌ Lỗi Tạo CV')
      .setDescription(result.error || 'Không thể tạo CV cho công việc được chỉ định.')
      .setFooter({ text: 'Job Hunter AI • Phase 4' });

    await interaction.editReply({ embeds: [errorEmbed] });
    return;
  }

  const resume = result.data;
  const verifiedIcon = resume.is_provenance_verified ? '🛡️' : '⚠️';

  const embed = new EmbedBuilder()
    .setColor(0x3498db)
    .setTitle(`📄 CV Đã Tinh Chỉnh: ${resume.target_title}`)
    .setDescription(
      `🌐 **[Mở trong Resume Workspace trên Web](${config.webAppUrl}/resume)**\n` +
      `Đã tạo thành công bản CV LaTeX và Cover Letter được tối ưu hóa cho công việc.\n` +
      `**Đảm bảo không bịa đặt thông tin (Zero Hallucination Guarantee).**`
    )
    .addFields(
      {
        name: '🎯 Vị Trí & Trạng Thái',
        value: `**Chức danh:** ${resume.target_title}\n**Trạng thái:** \`${resume.status}\`\n**Phiên bản:** v${resume.version}`,
        inline: true,
      },
      {
        name: `${verifiedIcon} Độ Xác Thực (Provenance)`,
        value: `**Điểm tin cậy:** \`${resume.provenance_score.toFixed(1)}%\`\n**Kiểm chứng:** ${
          resume.is_provenance_verified ? '✅ Đã xác minh' : '⚠️ Cần xem xét lại'
        }`,
        inline: true,
      },
      {
        name: '💡 Kỹ Năng Làm Nổi Bật',
        value: resume.matched_skills && resume.matched_skills.length > 0
          ? resume.matched_skills.map((s) => `\`${s}\``).join(', ')
          : '_Không có kỹ năng cụ thể nào được đánh dấu_',
        inline: false,
      }
    );

  if (resume.cover_letter) {
    const cl = resume.cover_letter;
    embed.addFields({
      name: '✉️ Cover Letter Hook Statement',
      value: cl.hook_statement ? `> *"${cl.hook_statement}"*` : '_Đã tạo nội dung Cover Letter_',
      inline: false,
    });
  }

  embed
    .setFooter({ text: `Resume ID: ${resume.id} • Dùng /apply ${resume.job_id} để nộp đơn` })
    .setTimestamp();

  // Tải file PDF nếu có
  const files: AttachmentBuilder[] = [];

  const pdfResult = await apiClient.downloadResumePdf(resume.id);
  if (pdfResult.success && pdfResult.data) {
    const pdfAttachment = new AttachmentBuilder(pdfResult.data, {
      name: `CV_Vy_Quoc_Huy_${resume.target_title.replace(/[\s/\\:]/g, '_')}.pdf`,
    });
    files.push(pdfAttachment);
  }

  // Đính kèm cover letter markdown nếu có
  if (resume.cover_letter) {
    const clBuffer = Buffer.from(resume.cover_letter.content_markdown, 'utf-8');
    const clAttachment = new AttachmentBuilder(clBuffer, {
      name: 'cover_letter.md',
    });
    files.push(clAttachment);
  }

  await interaction.editReply({
    embeds: [embed],
    files,
  });
}

export const resumeCommand = { data, execute };

