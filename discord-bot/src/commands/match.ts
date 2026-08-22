import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ChatInputCommandInteraction,
  EmbedBuilder,
  SlashCommandBuilder,
} from 'discord.js';
import { apiClient, JobMatchDetail } from '../services/api-client';
import { formatJobLink } from '../utils/formatters';
import { config } from '../config';

function renderScoreGauge(score: number): string {
  const totalBlocks = 10;
  const filledBlocks = Math.round((score / 100) * totalBlocks);
  let gauge = '';
  for (let i = 0; i < totalBlocks; i++) {
    if (i < filledBlocks) {
      gauge += score >= 80 ? '🟩' : score >= 60 ? '🟦' : score >= 40 ? '🟨' : '🟥';
    } else {
      gauge += '⬜';
    }
  }
  return `[${gauge}] **${score.toFixed(1)}/100**`;
}

function getRecommendationBadge(rec: string): { text: string; color: number } {
  switch (rec) {
    case 'STRONG_MATCH':
      return { text: '🌟 RẤT PHÙ HỢP (STRONG MATCH)', color: 0x2ecc71 };
    case 'GOOD_MATCH':
      return { text: '✅ PHÙ HỢP TỐT (GOOD MATCH)', color: 0x3498db };
    case 'REVIEW_REQUIRED':
      return { text: '⚠️ CẦN XEM XÉT THÊM (REVIEW REQUIRED)', color: 0xe67e22 };
    case 'WEAK_MATCH':
      return { text: '⚠️ PHÙ HỢP YẾU (WEAK MATCH)', color: 0xf39c12 };
    case 'DO_NOT_APPLY':
      return { text: '⛔ KHÔNG NÊN ỨNG TUYỂN (BLOCKED / DO NOT APPLY)', color: 0x7f8c8d };
    case 'POOR_MATCH':
    default:
      return { text: '❌ MỨC ĐỘ PHÙ HỢP THẤP (POOR MATCH)', color: 0xe74c3c };
  }
}

export const matchCommand = {
  data: new SlashCommandBuilder()
    .setName('match')
    .setDescription('Phân tích mức độ phù hợp giữa hồ sơ của bạn và tin tuyển dụng')
    .addStringOption((option) =>
      option
        .setName('id')
        .setDescription('ID hoặc UUID của tin tuyển dụng cần phân tích')
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

    // 1. Kích hoạt tính toán Match & lấy thông tin Job song song
    const [matchResult, jobResult] = await Promise.all([
      apiClient.calculateMatch(jobId, true),
      apiClient.getJobDetail(jobId),
    ]);

    if (!matchResult.success || !matchResult.data) {
      await interaction.editReply({
        content: `❌ **Không thể phân tích độ phù hợp:** ${matchResult.error}`,
      });
      return;
    }

    const match: JobMatchDetail = matchResult.data;
    const job = jobResult.data;
    const badge = getRecommendationBadge(match.recommendation);

    // 2. Định dạng Hard Filters
    const filterLines = match.hard_filter_results.map((f) => {
      const icon = f.status === 'PASS' ? '✅' : f.status === 'FAIL' ? '❌' : '⚠️';
      return `${icon} **${f.filter.toUpperCase()}:** ${f.reason}`;
    }).join('\n');

    // 3. Định dạng Kỹ năng
    const matchedSkillsStr = match.matched_skills.length > 0
      ? match.matched_skills.map((s) => `\`${s}\``).join(' ')
      : '*(Chưa khớp)*';

    const missingSkillsStr = match.missing_required_skills.length > 0
      ? match.missing_required_skills.map((s) => `\`${s}\``).join(' ')
      : '*(Không thiếu kỹ năng bắt buộc nào)*';

    // Helper an toàn không vượt quá giới hạn 1024 ký tự của Discord Embed Field
    const safeFieldVal = (val: string, maxLen = 1000) => {
      if (!val || !val.trim()) return '*(Không có)*';
      return val.length > maxLen ? val.substring(0, maxLen - 3) + '...' : val;
    };

    // 4. Định dạng 7 Tín hiệu (Chia làm 2 nhóm để không vượt quá 1024 ký tự)
    const signalDisplayNames: Record<string, string> = {
      requirement_fit: '🧠 Năng Lực & Phẩm Chất',
      technical_skill_match: '💻 Kỹ Năng Kỹ Thuật',
      project_relevance: '📁 Dự Án & Bằng Chứng',
      experience_relevance: '💼 Kinh Nghiệm Chuyên Môn',
      education_match: '🎓 Học Vấn & Bằng Cấp',
      seniority_match: '📈 Cấp Bậc Mục Tiêu',
      work_fit: '📍 Điều Kiện & Ca Làm Việc',
    };

    const formatSingleSignal = (s: any) => {
      const title = signalDisplayNames[s.name] || s.name;
      const statusBadge =
        s.evidence_status === 'NOT_REQUIRED'
          ? 'ℹ️ *Không yêu cầu*'
          : s.evidence_status === 'SUPPORTED'
          ? '✅ *Có bằng chứng*'
          : s.evidence_status === 'MISMATCH'
          ? '❌ *Không khớp*'
          : '⚠️ *Chưa đủ bằng chứng*';

      return `• **${title}:** \`${(s.score * 100).toFixed(0)}%\` *(${(s.weight * 100).toFixed(0)}%)* • ${statusBadge}\n  ↳ *${s.reason}*`;
    };

    const coreSignals = match.signals.filter((s) =>
      ['requirement_fit', 'technical_skill_match', 'project_relevance', 'experience_relevance'].includes(s.name)
    );
    const contextSignals = match.signals.filter((s) =>
      ['education_match', 'seniority_match', 'work_fit'].includes(s.name)
    );

    const coreSignalsSummary = coreSignals.map(formatSingleSignal).join('\n\n');
    const contextSignalsSummary = contextSignals.map(formatSingleSignal).join('\n\n');

    // 5. Thu thập các Evidence nổi bật
    const topEvidences: string[] = [];
    match.signals.forEach((s) => {
      if (s.evidence && s.evidence.length > 0) {
        s.evidence.forEach((ev) => {
          if (topEvidences.length < 3) {
            const shortExcerpt = ev.excerpt.length > 120 ? ev.excerpt.substring(0, 117) + '...' : ev.excerpt;
            topEvidences.push(`• **[${ev.source_type}] ${ev.title}:** ${shortExcerpt}`);
          }
        });
      }
    });

    const sourceUrl = job?.raw_job?.source_url || job?.source_url;

    const embed = new EmbedBuilder()
      .setTitle(`🎯 Phân Tích Độ Phù Hợp: ${match.job_snapshot?.title || job?.title || 'Job'} — ${match.job_snapshot?.company || job?.company_name || ''}`)
      .setColor(badge.color)
      .setDescription(
        `### ${renderScoreGauge(match.score)}\n**Kết luận:** ${badge.text}\n**Tư cách (Eligibility):** \`${match.eligibility}\``
      )
      .addFields(
        {
          name: '🛡️ Bộ Lọc Cứng (Hard Filters)',
          value: safeFieldVal(filterLines),
          inline: false,
        },
        {
          name: '✅ Kỹ Năng Kỹ Thuật Khớp',
          value: safeFieldVal(matchedSkillsStr),
          inline: true,
        },
        {
          name: '❌ Kỹ Năng Kỹ Thuật Còn Thiếu',
          value: safeFieldVal(missingSkillsStr),
          inline: true,
        },
        {
          name: '📊 Năng Lực Chuyên Môn & Dự Án (Trọng số 75%)',
          value: safeFieldVal(coreSignalsSummary),
          inline: false,
        },
        {
          name: '📋 Học Vấn, Cấp Bậc & Điều Kiện Làm Việc (Trọng số 25%)',
          value: safeFieldVal(contextSignalsSummary),
          inline: false,
        }
      );

    if (topEvidences.length > 0) {
      embed.addFields({
        name: '🧾 Bằng Chứng Đối Soát Nổi Bật (Evidence Trail)',
        value: safeFieldVal(topEvidences.join('\n')),
        inline: false,
      });
    }



    if (sourceUrl) {
      embed.addFields({
        name: '🌐 Link tuyển dụng gốc',
        value: formatJobLink(sourceUrl, job?.raw_job?.source || job?.source),
        inline: false,
      });
    }

    if (match.explanation) {
      embed.addFields({
        name: '💡 Nhận Xét & Lời Khuyên (AI / Rule-based Explanation)',
        value: match.explanation.length > 1000 ? match.explanation.substring(0, 1000) + '...' : match.explanation,
        inline: false,
      });
    }

    if (match.warnings && match.warnings.length > 0) {
      embed.addFields({
        name: '⚠️ Cảnh Báo Giới Hạn Điểm',
        value: match.warnings.join('\n'),
        inline: false,
      });
    }

    embed.setFooter({
      text: `Scoring Version: ${match.scoring_version} • Taxonomy Version: ${match.taxonomy_version} • Match ID: ${match.id.split('-')[0]}`,
    });
    embed.setTimestamp();

    // Action button to open link
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

