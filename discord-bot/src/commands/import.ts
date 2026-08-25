import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ChatInputCommandInteraction,
  EmbedBuilder,
  ModalBuilder,
  SlashCommandBuilder,
  TextInputBuilder,
  TextInputStyle,
} from 'discord.js';
import { apiClient, ManualJobIngestResult } from '../services/api-client';
import { formatJobLink } from '../utils/formatters';
import { config } from '../config';

export const importCommand = {
  data: new SlashCommandBuilder()
    .setName('import')
    .setDescription('📥 Nhập tin tuyển dụng thủ công từ văn bản thô hoặc đường dẫn web (Phase 2.5)')
    .addSubcommand((subcommand) =>
      subcommand
        .setName('url')
        .setDescription('Nhập tin tuyển dụng từ đường dẫn web trực tiếp (TopCV, ITViec, CareerLink...)')
        .addStringOption((option) =>
          option
            .setName('link')
            .setDescription('Đường dẫn URL của tin tuyển dụng')
            .setRequired(true)
        )
    )
    .addSubcommand((subcommand) =>
      subcommand
        .setName('text')
        .setDescription('Mở khung soạn thảo để dán bài đăng tuyển dụng thô (Facebook, Telegram, Email...)')
    ),

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
      await interaction.reply({
        content: '⛔ Bạn không có quyền sử dụng trợ lý cá nhân này.',
        ephemeral: true,
      });
      return;
    }

    const subcommand = interaction.options.getSubcommand();

    if (subcommand === 'url') {
      await interaction.deferReply({ ephemeral: false });

      const url = interaction.options.getString('link', true).trim();
      const result = await apiClient.ingestManualJob({
        mode: 'url',
        url: url,
        auto_match: true,
      });

      if (!result.success || !result.data) {
        await interaction.editReply({
          content: `❌ **Không thể nạp tin từ URL:** ${result.error}`,
        });
        return;
      }

      const { embed, components } = buildImportResultEmbed(result.data, url);
      await interaction.editReply({
        embeds: [embed],
        components,
      });
      return;
    }

    if (subcommand === 'text') {
      // Hiển thị Modal Textarea cho nội dung bài đăng dài
      const modal = new ModalBuilder()
        .setCustomId('modal_import_text')
        .setTitle('📝 Nhập Tin Tuyển Dụng Thô');

      const textInput = new TextInputBuilder()
        .setCustomId('input_raw_job_text')
        .setLabel('Nội dung bài đăng / Tin tuyển dụng:')
        .setStyle(TextInputStyle.Paragraph)
        .setPlaceholder('Dán toàn bộ bài đăng tuyển dụng vào đây (có tiêu đề, mức lương, kỹ năng, liên hệ)...')
        .setMinLength(30)
        .setMaxLength(4000)
        .setRequired(true);

      const actionRow = new ActionRowBuilder<TextInputBuilder>().addComponents(textInput);
      modal.addComponents(actionRow);

      await interaction.showModal(modal);
    }
  },
};

export function buildImportResultEmbed(
  res: ManualJobIngestResult,
  fallbackUrl?: string
): { embed: EmbedBuilder; components: ActionRowBuilder<ButtonBuilder>[] } {
  const job = res.job;
  const match = res.match;
  const meta = res.extraction_metadata;

  const statusEmoji = res.status === 'created' ? '🟢' : res.status === 'duplicate' ? '🟡' : '🟠';
  const statusTitle = res.status === 'created'
    ? 'ĐÃ NẠP THÀNH CÔNG (MỚI)'
    : res.status === 'duplicate'
    ? 'TIN TUYỂN DỤNG ĐÃ TỒN TẠI'
    : 'ĐÃ NẠP (MỘT SỐ TRƯỜNG THIẾU)';

  const embed = new EmbedBuilder()
    .setTitle(`${statusEmoji} ${job ? job.title : 'Tin tuyển dụng'} — ${job ? job.company_name : 'Công ty'}`)
    .setColor(res.status === 'created' ? 0x2ecc71 : res.status === 'duplicate' ? 0xf1c40f : 0xe67e22)
    .setDescription(res.message || 'Đã bóc tách và phân tích dữ liệu tuyển dụng thành công.')
    .setTimestamp();

  if (job) {
    const salaryText = job.is_salary_negotiable
      ? 'Thỏa thuận'
      : job.min_salary && job.max_salary
      ? `${job.min_salary.toLocaleString()} - ${job.max_salary.toLocaleString()} ${job.salary_currency || ''}`
      : 'Chưa công bố';

    embed.addFields(
      {
        name: '🏢 Cấp bậc & Hình thức',
        value: `\`${job.level}\` • \`${job.work_mode}\``,
        inline: true,
      },
      {
        name: '📍 Địa điểm',
        value: job.normalized_location || job.location || 'Vietnam',
        inline: true,
      },
      {
        name: '💰 Mức lương',
        value: salaryText,
        inline: true,
      }
    );

    const reqSkills = job.skills
      ?.filter((s) => s.is_required)
      .map((s) => `\`${s.canonical_name}\``)
      .join(', ') || 'Không có';

    embed.addFields({
      name: '🛠️ Kỹ năng trích xuất (Skills)',
      value: reqSkills,
      inline: false,
    });
  }

  if (meta) {
    const confidencePercent = Math.round((meta.overall_confidence || 0) * 100);
    embed.addFields({
      name: '📊 Độ tin cậy trích xuất',
      value: `\`${confidencePercent}%\` (Phương pháp: \`${meta.method}\`, Trạng thái: \`${meta.extraction_status}\`)`,
      inline: false,
    });

    if (meta.warnings && meta.warnings.length > 0) {
      embed.addFields({
        name: '⚠️ Lưu ý / Cảnh báo',
        value: meta.warnings.slice(0, 3).map((w) => `• ${w}`).join('\n'),
        inline: false,
      });
    }
  }

  if (match) {
    const scoreVal = Math.round(match.score || 0);
    embed.addFields({
      name: '🎯 Điểm phù hợp 7 tín hiệu (Match Score)',
      value: `**${scoreVal}/100** • Đánh giá: \`${match.recommendation}\` • Điều kiện: \`${match.eligibility}\``,
      inline: false,
    });

    if (match.explanation) {
      embed.addFields({
        name: '💡 Nhận xét nhanh',
        value: match.explanation.length > 300 ? match.explanation.substring(0, 300) + '...' : match.explanation,
        inline: false,
      });
    }
  }

  // Action row
  const row = new ActionRowBuilder<ButtonBuilder>();

  if (job) {
    const sourceUrl = job.raw_job?.source_url || job.source_url || fallbackUrl;
    if (sourceUrl && sourceUrl.startsWith('http')) {
      row.addComponents(
        new ButtonBuilder()
          .setLabel('🔗 Xem Tin Gốc')
          .setStyle(ButtonStyle.Link)
          .setURL(sourceUrl)
      );
    }
  }

  const components = row.components.length > 0 ? [row] : [];
  return { embed, components };
}
