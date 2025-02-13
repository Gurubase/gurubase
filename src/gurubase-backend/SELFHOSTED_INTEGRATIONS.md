# Self-Hosted Integrations Installation Instructions

## Slack

1. Go to https://api.slack.com/apps
2. Click "Create New App"
3. Select "From scratch"
4. Name it and pick your workspace
5. Open your backend to public. You can use `ngrok http $BACKEND_PORT` to do this
6. Go to "Event Subscriptions"
7. Enable it
8. Set this as request url:
    - `${public_backend_url}/slack/events`
9. Go to Event Subscriptions and add these as Subscribe to bot events:
    - `message.channels`
    - `message.groups`

<img src="imgs/slack-event-subscriptions.png" width="500"/>

10. Save changes
11. Go to "OAuth & Permissions"
12. Scroll to "Bot Token Scopes", and add the following permissions:
    - `channels:join`
    - `channels:read`
    - `chat:write`
    - `groups:read`
13. You should already have the following scopes while adding the event subscriptions. If not, add them as well:
    - `channels:history`
    - `groups:history`

<img src="imgs/slack-bot-permissions.png" width="500"/>

14. Go to "Install App"
15. Click "Install to ..."
16. Go through the OAuth flow
17. After installation, you will be redirected to the same page
18. Copy "Bot User OAuth Token"
19. Go to your guru's Slack integration page in the Gurubase UI
20. Paste the bot token you copied and click "Connect".
21. If the bot token is correct, you should be prompted to choose the channels and groups you want to connect to. Here, you can also send test messages to the channels/groups you saved.
22. Now you can ask questions to your guru in those channels via mentioning the bot.

## Discord

1. Upon installation, DiscordListener will start automatically. This will wait for valid bot tokens in the background.
2. Go to https://discord.com/developers/applications
3. Click "New Application" and follow up
4. Go to "Bot" and enable "Message Content Intent". This is required for the bot to read messages in the server.
5. Click "Save Changes"
6. Go to "Installation"
7. Under "Installation Contexts", de-select "User Install".
8. Under "Default Install Settings", and under "Guild Install", add "bot" to the "Scopes". Then, "Permissions" will become visible. Add "Send Messages" to the permissions.
![Discord Bot Permissions](imgs/discord-bot-permissions.png)
9. Click "Save Changes"
10. Go to the "Install Link" in your browser.
11. Pick the server you want to install the app to. And follow through the OAuth flow.
12. Then go to "Bot". There will be a "Token" subheader. Under it, click "Reset Token". Copy the new token.
13. Go to your guru's Discord integration page in the Gurubase UI
14. Paste the bot token you copied and click "Connect".
15. If the bot token is correct, you should be prompted to choose the channels you want to connect to. Here, you can also send test messages to the channels you saved.
16. After this step, DiscordListener should pick up the valid bot token and start listening to messages in the server.
17. Now you can ask questions to your guru in that server via mentioning the bot.
