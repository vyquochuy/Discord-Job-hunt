import {
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  ChatInputCommandInteraction,
  EmbedBuilder,
  ModalActionRowComponentBuilder,
  ModalBuilder,
  SlashCommandBuilder,
  TextInputBuilder,
  TextInputStyle,
} from 'discord.js';
import { apiClient, CandidateDetail } from '../services/api-client';
import { config } from '../config';

/**
 * Xây dựng Embed hiển thị Tổng quan Hồ sơ Ứng viên
 */
export function buildProfileOverviewEmbed(profile: CandidateDetail): EmbedBuilder {
  const eduInfo = profile.education.length > 0
    ? profile.education
        .map(
          (e) =>
            `🎓 **${e.institution}**\n• ${e.degree || 'Bachelor'} in ${e.field || 'Computer Science'}\n• GPA: \`${e.gpa || 'N/A'}\` | Niên khóa: \`${e.graduation_year || 'N/A'}\``
        )
        .join('\n\n')
    : '_Chưa cập nhật thông tin học vấn_';

  const roles = profile.target_roles.length > 0
    ? profile.target_roles.map((r) => `\`${r}\``).join(' • ')
    : '_Chưa thiết lập_';

  const locs = profile.target_locations.length > 0
    ? profile.target_locations.map((l) => `\`${l}\``).join(', ')
    : '_Chưa thiết lập_';

  const contactList: string[] = [];
  if (profile.email) contactList.push(`📧 **Email:** \`${profile.email}\``);
  if (profile.phone) contactList.push(`📱 **Phone:** \`${profile.phone}\``);
  if (profile.location) contactList.push(`📍 **Location:** \`${profile.location}\``);
  if (profile.github_url) contactList.push(`🐙 [GitHub](${profile.github_url})`);
  if (profile.linkedin_url) contactList.push(`💼 [LinkedIn](${profile.linkedin_url})`);

  return new EmbedBuilder()
    .setTitle(`👤 Hồ Sơ Ứng Viên: ${profile.full_name}`)
    .setDescription(
      `**Chức danh:** *${profile.headline || 'Software Engineer Intern'}*\n\n` +
      `> ${profile.summary || '_Chưa có tóm tắt mục tiêu nghề nghiệp_'}`
    )
    .setColor(0x3498db)
    .addFields(
      {
        name: '🎯 Vị Trí Mục Tiêu',
        value: roles,
        inline: false,
      },
      {
        name: '📍 Địa Điểm Làm Việc',
        value: locs,
        inline: true,
      },
      {
        name: '💼 Chính Sách Làm Việc',
        value: `\`${profile.preferences.remote || 'hybrid'}\``,
        inline: true,
      },
      {
        name: '🏫 Học Vấn & Đào Tạo',
        value: eduInfo,
        inline: false,
      },
      {
        name: '📞 Thông Tin Liên Hệ & Mạng Xã Hội',
        value: contactList.length > 0 ? contactList.join('\n') : '_Chưa có thông tin_',
        inline: false,
      },
      {
        name: '📊 Thống Kê Nguồn Bằng Chứng (Provenance)',
        value: `• **Kỹ năng (Skills):** \`${profile.skills.length}\` kỹ năng\n• **Dự án (Projects):** \`${profile.projects.length}\` dự án (kèm evidence points)\n• **Kinh nghiệm (Experience):** \`${profile.experiences.length}\` mục`,
        inline: false,
      }
    )
    .setFooter({
      text: `ID: ${profile.id} • Cập nhật lúc ${new Date(profile.updated_at).toLocaleString('vi-VN')}`,
    })
    .setTimestamp();
}

/**
 * Xây dựng Embed hiển thị Chi tiết Kỹ năng (Skills)
 */
export function buildProfileSkillsEmbed(profile: CandidateDetail): EmbedBuilder {
  const embed = new EmbedBuilder()
    .setTitle(`🛠️ Danh Mục Kỹ Năng: ${profile.full_name}`)
    .setColor(0x2ecc71)
    .setDescription('Tất cả kỹ năng đã được xác thực từ hồ sơ gốc:');

  const grouped: Record<string, string[]> = {};
  for (const skill of profile.skills) {
    const cat = skill.category.toUpperCase().replace('_', ' ');
    if (!grouped[cat]) grouped[cat] = [];
    const prof = skill.proficiency ? ` (${skill.proficiency})` : '';
    grouped[cat].push(`\`${skill.name}\`${prof}`);
  }

  for (const [category, skillNames] of Object.entries(grouped)) {
    embed.addFields({
      name: `📌 ${category}`,
      value: skillNames.join(' • ') || '_Trống_',
      inline: false,
    });
  }

  embed.setFooter({ text: 'AI Job Hunter • Candidate Skills Matrix' });
  return embed;
}

/**
 * Xây dựng Embed hiển thị Chi tiết Dự án & Minh chứng Kỹ thuật
 */
export function buildProfileProjectsEmbed(profile: CandidateDetail): EmbedBuilder {
  const embed = new EmbedBuilder()
    .setTitle(`🚀 Dự Án & Minh Chứng Kỹ Thuật (Evidence Points)`)
    .setColor(0x9b59b6)
    .setDescription('Danh sách các dự án thực tế kèm số liệu đo lường định lượng:');

  for (const proj of profile.projects) {
    let links = '';
    if (proj.repository_url) links += `[GitHub Repo](${proj.repository_url}) `;
    if (proj.demo_url) links += `• [Live Demo](${proj.demo_url})`;

    const tech = proj.technologies.length > 0
      ? `\n🛠️ **Tech:** ` + proj.technologies.map((t) => `\`${t}\``).join(' ')
      : '';

    let evidenceStr = '';
    if (proj.evidence_points && proj.evidence_points.length > 0) {
      evidenceStr = '\n**Minh chứng kỹ thuật:**\n' +
        proj.evidence_points
          .map((ev) => `• **${ev.title}:** ${ev.detail}`)
          .join('\n');
    }

    embed.addFields({
      name: `💻 ${proj.name} ${proj.role ? `(${proj.role})` : ''} — \`${proj.period || 'N/A'}\``,
      value: `*${proj.summary || ''}*\n${links}${tech}${evidenceStr}`.slice(0, 1024),
      inline: false,
    });
  }

  embed.setFooter({ text: 'AI Job Hunter • Provenance & Evidence Verification' });
  return embed;
}

/**
 * Tạo Hàng nút bấm tương tác (Action Buttons)
 */
export function buildProfileButtons(): ActionRowBuilder<ButtonBuilder> {
  return new ActionRowBuilder<ButtonBuilder>().addComponents(
    new ButtonBuilder()
      .setCustomId('btn_profile_overview')
      .setLabel('Tổng Quan')
      .setEmoji('👤')
      .setStyle(ButtonStyle.Primary),
    new ButtonBuilder()
      .setCustomId('btn_profile_skills')
      .setLabel('Kỹ Năng')
      .setEmoji('🛠️')
      .setStyle(ButtonStyle.Secondary),
    new ButtonBuilder()
      .setCustomId('btn_profile_projects')
      .setLabel('Dự Án')
      .setEmoji('🚀')
      .setStyle(ButtonStyle.Secondary),
    new ButtonBuilder()
      .setCustomId('btn_profile_sync')
      .setLabel('Đồng Bộ Context')
      .setEmoji('🔄')
      .setStyle(ButtonStyle.Success)
  );
}

export const profileCommand = {
  data: new SlashCommandBuilder()
    .setName('profile')
    .setDescription('Xem, chỉnh sửa hoặc đồng bộ hồ sơ ứng viên cá nhân')
    .addSubcommand((sub) =>
      sub
        .setName('view')
        .setDescription('Xem toàn bộ thông tin hồ sơ ứng viên và bằng chứng')
    )
    .addSubcommand((sub) =>
      sub
        .setName('update')
        .setDescription('Mở hộp thoại chỉnh sửa nhanh thông tin hồ sơ')
    )
    .addSubcommand((sub) =>
      sub
        .setName('sync')
        .setDescription('Kích hoạt đồng bộ hóa dữ liệu từ các file context/')
    ),

  async execute(interaction: ChatInputCommandInteraction): Promise<void> {
    // Kiểm tra quyền truy cập cá nhân
    if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
      await interaction.reply({
        content: '⛔ Bạn không có quyền sử dụng trợ lý cá nhân này.',
        ephemeral: true,
      });
      return;
    }

    const subcommand = interaction.options.getSubcommand();

    // 1. Lệnh /profile update -> Mở Modal
    if (subcommand === 'update') {
      const modal = new ModalBuilder()
        .setCustomId('modal_profile_update')
        .setTitle('Chỉnh Sửa Hồ Sơ Ứng Viên');

      const headlineInput = new TextInputBuilder()
        .setCustomId('input_headline')
        .setLabel('Chức danh / Headline')
        .setStyle(TextInputStyle.Short)
        .setPlaceholder('ví dụ: System Intern / DevOps Engineer Intern')
        .setRequired(false);

      const locationInput = new TextInputBuilder()
        .setCustomId('input_location')
        .setLabel('Địa điểm làm việc')
        .setStyle(TextInputStyle.Short)
        .setPlaceholder('ví dụ: Thu Duc, Ho Chi Minh')
        .setRequired(false);

      const targetRolesInput = new TextInputBuilder()
        .setCustomId('input_target_roles')
        .setLabel('Vị trí mục tiêu (phân cách bởi dấu phẩy)')
        .setStyle(TextInputStyle.Short)
        .setPlaceholder('ví dụ: System Intern, DevOps, Backend')
        .setRequired(false);

      const summaryInput = new TextInputBuilder()
        .setCustomId('input_summary')
        .setLabel('Mục tiêu nghề nghiệp / Summary')
        .setStyle(TextInputStyle.Paragraph)
        .setPlaceholder('Nhập tóm tắt mục tiêu ngắn gọn...')
        .setRequired(false);

      modal.addComponents(
        new ActionRowBuilder<ModalActionRowComponentBuilder>().addComponents(headlineInput),
        new ActionRowBuilder<ModalActionRowComponentBuilder>().addComponents(locationInput),
        new ActionRowBuilder<ModalActionRowComponentBuilder>().addComponents(targetRolesInput),
        new ActionRowBuilder<ModalActionRowComponentBuilder>().addComponents(summaryInput)
      );

      await interaction.showModal(modal);
      return;
    }

    // 2. Lệnh /profile sync -> Đồng bộ hóa
    if (subcommand === 'sync') {
      await interaction.deferReply({ ephemeral: false });

      const syncResult = await apiClient.syncProfile();
      if (!syncResult.success || !syncResult.data) {
        await interaction.editReply({
          content: `❌ **Đồng bộ hóa thất bại:** ${syncResult.error}`,
        });
        return;
      }

      const syncData = syncResult.data;
      const syncEmbed = new EmbedBuilder()
        .setTitle('✅ Đồng Bộ Hồ Sơ Thành Công!')
        .setDescription(
          `Hệ thống đã nạp thành công dữ liệu từ thư mục \`context/\` vào cơ sở dữ liệu PostgreSQL:`
        )
        .setColor(0x2ecc71)
        .addFields(
          { name: '👤 Ứng viên', value: `\`${syncData.full_name}\``, inline: true },
          { name: '🛠️ Kỹ năng', value: `\`${syncData.skills_count}\` items`, inline: true },
          { name: '🚀 Dự án', value: `\`${syncData.projects_count}\` projects`, inline: true },
          { name: '💼 Kinh nghiệm', value: `\`${syncData.experiences_count}\` records`, inline: true },
          { name: '📜 Chứng chỉ', value: `\`${syncData.certifications_count}\` certs`, inline: true }
        )
        .setFooter({ text: 'AI Job Hunter • Candidate Sync Service' })
        .setTimestamp();

      await interaction.editReply({
        embeds: [syncEmbed],
        components: [buildProfileButtons()],
      });
      return;
    }

    // 3. Lệnh /profile view (mặc định) -> Hiển thị Overview
    await interaction.deferReply({ ephemeral: false });
    const profileResult = await apiClient.getProfile();

    if (!profileResult.success || !profileResult.data) {
      await interaction.editReply({
        content: `❌ **Không thể lấy hồ sơ:** ${profileResult.error}`,
      });
      return;
    }

    const overviewEmbed = buildProfileOverviewEmbed(profileResult.data);
    await interaction.editReply({
      embeds: [overviewEmbed],
      components: [buildProfileButtons()],
    });
  },
};
