# Anonymous Chat Bot 🤖

A Telegram bot for anonymous chatting with strangers. Users can exchange messages, photos, videos, and stickers while maintaining their privacy.

## Features
- Anonymous text/photo/video/sticker chats
- User matching system
- Content moderation
- Report system
- Admin controls and monitoring
- User blocking system
- Donation system
- Activity tracking
- Inactivity cleanup

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/royalashu4u/kuu.git
   cd kuu
   ```

2. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_USER_ID=your_telegram_user_id
   DONATION_LINK=your_donation_link
   ```

4. Run the bot:
   ```bash
   python app.py
   ```

## Commands
- `/start` - Start the bot and find a chat partner
- `/find` - Find a new chat partner
- `/next` - Skip current partner and find a new one
- `/stop` - End current chat
- `/report` - Report current chat partner
- `/settings` - Configure user preferences
- `/donate` - Support the bot
- `/help` - Show help information
- `/id` - Show your user ID

## Admin Commands
- `/admin` - Access admin panel
- `/full` - Get full user information
- `/list` - List all users

## Environment Variables
- `BOT_TOKEN` - Your Telegram Bot Token from @BotFather
- `ADMIN_USER_ID` - Telegram User ID of the admin
- `DONATION_LINK` - Link for donations (optional)

## Deployment
The bot is ready to be deployed on platforms like Heroku with the included `Procfile` and `nixpacks.toml`.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)