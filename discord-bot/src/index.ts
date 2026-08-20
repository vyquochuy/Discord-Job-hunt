import {
  Client,
  Collection,
  Events,
  GatewayIntentBits,
  REST,
  Routes,
} from 'discord.js';
import { config, validateConfig } from './config';
import { pingCommand } from './commands/ping';

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

// 4. Sự kiện khi Bot sẵn sàng (Ready)
client.once(Events.ClientReady, async (readyClient) => {
  console.log(`🤖 Discord Bot đã đăng nhập thành công dưới tên: ${readyClient.user.tag}`);

  // Tự động đăng ký Slash Commands với Discord Gateway
  if (!config.discordToken || !config.clientId) {
    console.log('ℹ️ Bỏ qua bước đăng ký Slash Command vì chưa có Token/Client ID.');
    return;
  }

  const rest = new REST({ version: '10' }).setToken(config.discordToken);
  const commandData = [pingCommand.data.toJSON()];

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
  if (!interaction.isChatInputCommand()) return;

  const command = commands.get(interaction.commandName);
  if (!command) {
    console.error(`Không tìm thấy lệnh: ${interaction.commandName}`);
    return;
  }

  try {
    await command.execute(interaction);
  } catch (error) {
    console.error(`Lỗi khi thực thi lệnh /${interaction.commandName}:`, error);
    const errorMessage = '⚠️ Đã xảy ra lỗi nội bộ khi xử lý lệnh của bạn.';
    if (interaction.replied || interaction.deferred) {
      await interaction.followUp({ content: errorMessage, ephemeral: true });
    } else {
      await interaction.reply({ content: errorMessage, ephemeral: true });
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
