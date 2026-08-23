import {
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient, JobItem } from '../services/api-client';
import { formatJobLink } from '../utils/formatters';
import { config } from '../config';


export const jobsCommand = {
  data: new SlashCommandBuilder()
    .setName('jobs')
    .setDescription('Tìm kiếm và duyệt các tin tuyển dụng đang hoạt động')
    .addStringOption((option) =>
      option
        .setName('keyword')
        .setDescription('Từ khóa tìm kiếm (tiêu đề, công ty, kỹ năng)')
        .setRequired(false)
    )
    .addStringOption((option) =>
      option
        .setName('work_mode')
        .setDescription('Hình thức làm việc')
        .setRequired(false)
        .addChoices(
          { name: 'Remote (Từ xa)', value: 'REMOTE' },
          { name: 'Hybrid (Linh hoạt)', value: 'HYBRID' },
          { name: 'Onsite (Tại văn phòng)', value: 'ONSITE' }
        )
    )
    .addStringOption((option) =>
      option
        .setName('level')
        .setDescription('Cấp bậc công việc')
        .setRequired(false)
        .addChoices(
          { name: 'Intern (Thực tập)', value: 'INTERN' },
          { name: 'Fresher (Mới tốt nghiệp)', value: 'FRESHER' },
          { name: 'Junior', value: 'JUNIOR' },
          { name: 'Mid-level', value: 'MID' },
          { name: 'Senior', value: 'SENIOR' },
          { name: 'Tech Lead / Manager', value: 'LEAD' }
        )
    )
    .addIntegerOption((option) =>
      option
        .setName('page')
        .setDescription('Số trang')
        .setMinValue(1)
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

    const keyword = interaction.options.getString('keyword') || undefined;
    const workMode = interaction.options.getString('work_mode') || undefined;
    const level = interaction.options.getString('level') || undefined;
    const page = interaction.options.getInteger('page') || 1;

    const result = await apiClient.getJobs({
      keyword,
      work_mode: workMode,
      level,
      page,
      page_size: 6,
    });

    if (!result.success || !result.data) {
      await interaction.editReply({
        content: `❌ **Lỗi khi lấy danh sách việc làm:** ${result.error}`,
      });
      return;
    }

    const { items, total, page_size } = result.data;
    const totalPages = Math.ceil(total / page_size) || 1;

    if (items.length === 0) {
      const emptyEmbed = new EmbedBuilder()
        .setTitle('🔍 Không Tìm Thấy Tin Tuyển Dụng')
        .setDescription('Không có tin tuyển dụng nào phù hợp với bộ lọc hiện tại.')
        .setColor(0x95a5a6)
        .addFields({
          name: '💡 Gợi ý',
          value: 'Hãy thử tìm kiếm với từ khóa khác hoặc bỏ bớt điều kiện lọc.',
        });
      await interaction.editReply({ embeds: [emptyEmbed] });
      return;
    }

    const embed = new EmbedBuilder()
      .setTitle(`💼 Danh Sách Tin Tuyển Dụng (${total} việc làm)`)
      .setDescription(
        `🌐 **[Mở trên Web Application để xem & phân tích trực quan](${config.webAppUrl}/jobs)**\n` +
        `Trang **${page}/${totalPages}** • Dùng lệnh \`/job <id>\` để xem chi tiết hoặc \`/match <id>\` để phân tích độ phù hợp.`
      )
      .setColor(0x3498db);

    items.forEach((job: JobItem, index: number) => {
      const salaryText = job.is_salary_negotiable
        ? 'Thỏa thuận'
        : job.min_salary && job.max_salary
        ? `${job.min_salary.toLocaleString()} - ${job.max_salary.toLocaleString()} ${job.salary_currency || ''}`
        : 'Chưa công bố';

      const shortId = job.id.split('-')[0];
      const levelBadge = `\`${job.level}\``;
      const modeBadge = `\`${job.work_mode}\``;

      const linkText = formatJobLink(job.source_url, job.source);

      embed.addFields({
        name: `${(page - 1) * page_size + index + 1}. ${job.title} — ${job.company_name}`,
        value: `📍 **Địa điểm:** ${job.normalized_location || job.location || 'N/A'}\n🏢 **Cấp bậc / Hình thức:** ${levelBadge} • ${modeBadge}\n💰 **Mức lương:** ${salaryText}\n🌐 **Link gốc:** ${linkText}\n🆔 **Job ID:** \`${job.id}\` (Rút gọn: \`${shortId}\`)`,
        inline: false,
      });

    });

    embed.setFooter({
      text: `AI Job Hunter • Phase 3 Job Intelligence • Trang ${page}/${totalPages}`,
    });
    embed.setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  },
};
