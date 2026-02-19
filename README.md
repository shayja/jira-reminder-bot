# Jira Reminder Bot 🦞

A Python-based automation to sync Jira tasks and Telegram reminders.

## 🚀 Setup

1. **Clone the repo**

2. Install Dependencies

Bash
pip install -r requirements.txt

3. **Create a Virtual Environment (Recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

Configure Environment Variables
Create a .env file in the root directory:

```env
# Jira Configuration
JIRA_URL=https://<YOUR_COMPANY>.atlassian.net
JIRA_EMAIL=<YOUR_EMAIL>
JIRA_API_TOKEN=your_jira_token_here # Get at: [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

# Telegram Configuration
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Run the Bot

Bash
python app.py
