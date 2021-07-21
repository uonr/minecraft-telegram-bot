# minecraft-telegram-bot

一个自动读取服务器日志，在游戏和 Telegram 之间转发数据的 bot

## 如何使用？


1. 注册个 bot
2. 拉进群，给 bot 管理员权限（至少要给改群名的权限，或者不用在线人数功能）
3. [获得群 chat id](https://stackoverflow.com/questions/32423837/telegram-bot-how-to-get-a-group-chat-id)
4. 打开 minecraft 的 rcon 功能，并且设置密码 （`server.properties` 中 `rcon.password=你的密码` `enable-rcon=true`）
5. 克隆仓库，安装依赖 `pip3 install -r requirements.txt`
6. 新建一个 `.env` 文件，内容照着 `.env.example` 设置。
7. 启动

## 设置解释

```bash
# Minecraft 日志文件路径
LOG_FILE_PATH=../minecraft/logs/latest.log 
# Telegram bot token 你需要给 bot 管理员权限或者在 bot 设置中开启看群消息
BOT_TOKEN=123456789:ABCDEFGHIJKLMN 
# 群的 CHAT_ID
CHAT_ID=-10086
# 在群名上显示在线数的功能，需要在这里写
CHAT_TITLE=禁止炸鱼
# rcon 的密码
RCON_PASSWORD=asdfasdf
```

