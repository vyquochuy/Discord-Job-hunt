import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient } from '../services/api-client';
import { formatJobLink } from '../utils/formatters';
import { config } from '../config';


export const jobCommand = {
  data: new SlashCommandBuilder()
    .setName('job')
    .setDescription('Xem chi tiết một tin tuyển dụng theo ID')
    .addStringOption((option) =>
      option
        .setName('id')
        .setDescription('ID hoặc UUID của tin tuyển dụng')
        .setRequired(true)
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

    const jobId = interaction.options.getString('id', true).trim();
    const result = await apiClient.getJobDetail(jobId);

    if (!result.success || !result.data) {
      await interaction.editReply({
        content: `❌ **Không tìm thấy tin tuyển dụng:** ${result.error}`,
      });
      return;
    }

    const job = result.data;

    const salaryText = job.is_salary_negotiable
      ? 'Thỏa thuận'
      : job.min_salary && job.max_salary
      ? `${job.min_salary.toLocaleString()} - ${job.max_salary.toLocaleString()} ${job.salary_currency || ''}`
      : 'Chưa công bố';

    const reqSkills = job.skills
      .filter((s) => s.is_required)
      .map((s) => `\`${s.canonical_name}\``)
      .join(', ') || 'Không có';

    const prefSkills = job.skills
      .filter((s) => !s.is_required)
      .map((s) => `\`${s.canonical_name}\``)
      .join(', ') || 'Không có';

    const descExcerpt =
      job.requirements_summary ||
      (job.description.length > 500
        ? job.description.substring(0, 500) + '...'
        : job.description);

    const embed = new EmbedBuilder()
      .setTitle(`📋 ${job.title} — ${job.company_name}`)
      .setDescription(descExcerpt)
      .setColor(0x1abc9c)
      .addFields(
        {
          name: '🏢 Cấp bậc & Hình thức',
          value: `\`${job.level}\` • \`${job.work_mode}\``,
          inline: true,
        },
        {
          name: '📍 Địa điểm',
          value: job.normalized_location || job.location || 'N/A',
          inline: true,
        },
        {
          name: '💰 Mức lương',
          value: salaryText,
          inline: true,
        },
        {
          name: '🛠️ Kỹ năng bắt buộc (Required)',
          value: reqSkills,
          inline: false,
        },
        {
          name: '✨ Kỹ năng ưu tiên (Nice-to-have)',
          value: prefSkills,
          inline: false,
        }
      );

    const sourceUrl = job.raw_job?.source_url || job.source_url;
    if (sourceUrl) {
      embed.addFields({
        name: '🌐 Link tuyển dụng gốc',
        value: formatJobLink(sourceUrl, job.raw_job?.source || job.source),
        inline: false,
      });
    }

    if (job.benefits_summary) {
      embed.addFields({
        name: '🎁 Quyền lợi & Phúc lợi',
        value: job.benefits_summary,
        inline: false,
      });
    }

    embed.setFooter({
      text: `Job ID: ${job.id} • Dùng /match ${job.id} để phân tích độ phù hợp`,
    });
    embed.setTimestamp();

    // Action buttons
    const row = new ActionRowBuilder<ButtonBuilder>();

    if (sourceUrl) {
      let domainLabel = 'Xem Tin Gốc';
      try {
        const parsed = new URL(sourceUrl);
        domainLabel = `Mở trên ${parsed.hostname.replace(/^www\./, '')}`;
      } catch {}

      row.addComponents(
        new ButtonBuilder()
          .setLabel(`🔗 ${domainLabel}`)
          .setStyle(ButtonStyle.Link)
          .setURL(sourceUrl)
      );
    }


    const components = row.components.length > 0 ? [row] : [];

    await interaction.editReply({
      embeds: [embed],
      components,
    });
  },
};
