import {
  Client,
  Collection,
  EmbedBuilder,
  Events,
  GatewayIntentBits,
  REST,
  Routes,
} from 'discord.js';
import { config, validateConfig } from './config';
import { pingCommand } from './commands/ping';
import {
  profileCommand,
  buildProfileOverviewEmbed,
  buildProfileSkillsEmbed,
  buildProfileProjectsEmbed,
  buildProfileButtons,
} from './commands/profile';
import { jobsCommand } from './commands/jobs';
import { jobCommand } from './commands/job';
import { matchCommand } from './commands/match';
import { recommendCommand } from './commands/recommend';
import { collectCommand } from './commands/collect';
import { resumeCommand } from './commands/resume';
import { applyCommand } from './commands/apply';
import { importCommand, buildImportResultEmbed } from './commands/import';
import { apiClient } from './services/api-client';

// 1. Kiểm tra cấu hình môi trường
validateConfig();

// 2. Khởi tạo Discord Client
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.DirectMessages,
  ],
});

// 3. Đăng ký danh sách Slash Commands
const commands = new Collection<string, any>();
commands.set(pingCommand.data.name, pingCommand);
commands.set(profileCommand.data.name, profileCommand);
commands.set(jobsCommand.data.name, jobsCommand);
commands.set(jobCommand.data.name, jobCommand);
commands.set(matchCommand.data.name, matchCommand);
commands.set(recommendCommand.data.name, recommendCommand);
commands.set(collectCommand.data.name, collectCommand);
commands.set(resumeCommand.data.name, resumeCommand);
commands.set(applyCommand.data.name, applyCommand);
commands.set(importCommand.data.name, importCommand);

// 4. Sự kiện khi Bot sẵn sàng (Ready)
client.once(Events.ClientReady, async (readyClient) => {
  console.log(`🤖 Discord Bot đã đăng nhập thành công dưới tên: ${readyClient.user.tag}`);

  // Tự động đăng ký Slash Commands với Discord Gateway
  if (!config.discordToken || !config.clientId) {
    console.log('ℹ️ Bỏ qua bước đăng ký Slash Command vì chưa có Token/Client ID.');
    return;
  }

  const rest = new REST({ version: '10' }).setToken(config.discordToken);
  const commandData = [
    pingCommand.data.toJSON(),
    profileCommand.data.toJSON(),
    jobsCommand.data.toJSON(),
    jobCommand.data.toJSON(),
    matchCommand.data.toJSON(),
    recommendCommand.data.toJSON(),
    collectCommand.data.toJSON(),
    resumeCommand.data.toJSON(),
    applyCommand.data.toJSON(),
    importCommand.data.toJSON(),
  ];



  try {
    console.log('🔄 Đang đồng bộ Slash Commands lên Discord...');
    if (config.guildId) {
      // Đăng ký cho 1 Guild/Server cụ thể (Cập nhật ngay lập tức cho mục đích phát triển)
      await rest.put(
        Routes.applicationGuildCommands(config.clientId, config.guildId),
        { body: commandData }
      );
      console.log(`✅ Đã đăng ký thành công ${commandData.length} Slash Command cho Server (${config.guildId}).`);
    } else {
      // Đăng ký Global cho toàn bộ Discord
      await rest.put(
        Routes.applicationCommands(config.clientId),
        { body: commandData }
      );
      console.log(`✅ Đã đăng ký thành công ${commandData.length} Global Slash Command.`);
    }
  } catch (error) {
    console.error('❌ Lỗi khi đăng ký Slash Command:', error);
  }
});

// 5. Sự kiện tiếp nhận tương tác từ người dùng (InteractionCreate)
client.on(Events.InteractionCreate, async (interaction) => {
  // A. Xử lý Slash Commands
  if (interaction.isChatInputCommand()) {
    const command = commands.get(interaction.commandName);
    if (!command) {
      console.error(`Không tìm thấy lệnh: ${interaction.commandName}`);
      return;
    }

    try {
      await command.execute(interaction);
    } catch (error) {
      console.error(`Lỗi khi thực thi lệnh /${interaction.commandName}:`, error);
      const errorMessage = '⚠️ Đã xảy ra lỗi nội bộ khi xử lý lệnh của bạn. Vui lòng thử lại sau giây lát.';
      try {
        if (interaction.deferred && !interaction.replied) {
          await interaction.editReply({ content: errorMessage });
        } else if (interaction.replied) {
          await interaction.followUp({ content: errorMessage, flags: [64] });
        } else {
          await interaction.reply({ content: errorMessage, flags: [64] });
        }
      } catch (err: any) {
        console.warn(`Không thể gửi phản hồi lỗi interaction (${interaction.commandName}):`, err.message);
      }
    }
    return;
  }

  // B. Xử lý Modal Submits (Chỉnh sửa hồ sơ nhanh)
  if (interaction.isModalSubmit()) {
    if (interaction.customId === 'modal_profile_update') {
      if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
        await interaction.reply({
          content: '⛔ Bạn không có quyền chỉnh sửa hồ sơ này.',
          ephemeral: true,
        });
        return;
      }

      await interaction.deferReply({ ephemeral: false });

      const headline = interaction.fields.getTextInputValue('input_headline').trim();
      const location = interaction.fields.getTextInputValue('input_location').trim();
      const targetRolesRaw = interaction.fields.getTextInputValue('input_target_roles').trim();
      const summary = interaction.fields.getTextInputValue('input_summary').trim();

      const updatePayload: Record<string, any> = {};
      if (headline) updatePayload.headline = headline;
      if (location) updatePayload.location = location;
      if (summary) updatePayload.summary = summary;
      if (targetRolesRaw) {
        updatePayload.target_roles = targetRolesRaw
          .split(',')
          .map((r) => r.trim())
          .filter(Boolean);
      }

      const updateResult = await apiClient.updateProfile(updatePayload);
      if (!updateResult.success || !updateResult.data) {
        await interaction.editReply({
          content: `❌ **Cập nhật thất bại:** ${updateResult.error}`,
        });
        return;
      }

      const updatedEmbed = buildProfileOverviewEmbed(updateResult.data);
      await interaction.editReply({
        content: '✨ **Đã cập nhật hồ sơ ứng viên thành công!**',
        embeds: [updatedEmbed],
        components: [buildProfileButtons()],
      });
    }

    if (interaction.customId === 'modal_import_text') {
      if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
        await interaction.reply({
          content: '⛔ Bạn không có quyền nạp tin tuyển dụng này.',
          ephemeral: true,
        });
        return;
      }

      await interaction.deferReply({ ephemeral: false });

      const rawText = interaction.fields.getTextInputValue('input_raw_job_text').trim();
      const result = await apiClient.ingestManualJob({
        mode: 'text',
        raw_text: rawText,
        auto_match: true,
      });

      if (!result.success || !result.data) {
        await interaction.editReply({
          content: `❌ **Nạp tin tuyển dụng thất bại:** ${result.error}`,
        });
        return;
      }

      const { embed, components } = buildImportResultEmbed(result.data);
      await interaction.editReply({
        embeds: [embed],
        components,
      });
    }
    return;
  }

  // C. Xử lý Button Clicks (Chuyển đổi view Profile và Đồng bộ)
  if (interaction.isButton()) {
    if (config.allowedUserId && interaction.user.id !== config.allowedUserId) {
      await interaction.reply({
        content: '⛔ Bạn không có quyền tương tác với bảng điều khiển này.',
        ephemeral: true,
      });
      return;
    }

    const buttonId = interaction.customId;

    if (buttonId.startsWith('btn_profile_')) {
      await interaction.deferUpdate();

      if (buttonId === 'btn_profile_sync') {
        const syncResult = await apiClient.syncProfile();
        if (!syncResult.success || !syncResult.data) {
          await interaction.followUp({
            content: `❌ **Đồng bộ thất bại:** ${syncResult.error}`,
            ephemeral: true,
          });
          return;
        }

        const syncData = syncResult.data;
        const syncEmbed = new EmbedBuilder()
          .setTitle('✅ Đồng Bộ Hồ Sơ Thành Công!')
          .setDescription(`Dữ liệu từ thư mục \`context/\` đã được nạp mới:`)
          .setColor(0x2ecc71)
          .addFields(
            { name: '👤 Ứng viên', value: `\`${syncData.full_name}\``, inline: true },
            { name: '🛠️ Kỹ năng', value: `\`${syncData.skills_count}\``, inline: true },
            { name: '🚀 Dự án', value: `\`${syncData.projects_count}\``, inline: true },
            { name: '💼 Kinh nghiệm', value: `\`${syncData.experiences_count}\``, inline: true },
            { name: '📜 Chứng chỉ', value: `\`${syncData.certifications_count}\``, inline: true }
          )
          .setFooter({ text: 'AI Job Hunter • Candidate Sync Service' })
          .setTimestamp();

        await interaction.editReply({
          embeds: [syncEmbed],
          components: [buildProfileButtons()],
        });
        return;
      }

      // Lấy profile data cho các view buttons
      const profileResult = await apiClient.getProfile();
      if (!profileResult.success || !profileResult.data) {
        await interaction.followUp({
          content: `❌ **Không thể lấy hồ sơ:** ${profileResult.error}`,
          ephemeral: true,
        });
        return;
      }

      let embed: EmbedBuilder;
      if (buttonId === 'btn_profile_skills') {
        embed = buildProfileSkillsEmbed(profileResult.data);
      } else if (buttonId === 'btn_profile_projects') {
        embed = buildProfileProjectsEmbed(profileResult.data);
      } else {
        embed = buildProfileOverviewEmbed(profileResult.data);
      }

      await interaction.editReply({
        embeds: [embed],
        components: [buildProfileButtons()],
      });
    }
  }
});

// 6. Đăng nhập Bot nếu có Token
if (config.discordToken) {
  client.login(config.discordToken).catch((err) => {
    console.error('❌ Không thể đăng nhập Discord Bot:', err.message);
  });
} else {
  console.log('ℹ️ DISCORD_TOKEN chưa được cung cấp. Bot đang ở chế độ chờ cấu hình .env');
}
