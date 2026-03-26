# CeylonVest Pulse — Claude Code Setup Guide

## Step 1: Get your accounts sorted

You need two things before touching any code:

**A. Claude Pro or Max subscription ($20-100/month)**
- Go to claude.ai/pricing
- You need at least Pro ($20/month) — Claude Code doesn't work on the free plan
- If you're doing heavy development, Max ($100/month) gives 20x more usage
- You already have a Claude account, so just upgrade if you haven't

**B. An Anthropic API key (for the bot's sentiment scoring)**
- Go to console.anthropic.com
- Sign up / sign in
- Go to "API Keys" in the sidebar
- Click "Create Key"
- Copy it — starts with `sk-ant-`
- You'll need this later for the bot's .env file
- Add ~$20 in credits to start (the bot uses very little per day)

**C. A Telegram Bot Token**
- Open Telegram, search for @BotFather
- Send `/newbot`
- Name it "CeylonVest Pulse" (or whatever you want)
- Username: `ceylonvest_pulse_bot` (must end in `bot`)
- BotFather gives you a token — save it

---

## Step 2: Install Claude Code

You're on Windows (Pickering, Canada). Here's exactly what to do:

**A. Install Git for Windows (required first)**
1. Go to https://git-scm.com/download/win
2. Download the installer
3. Run it — click "Next" on every screen, leave all defaults
4. Restart your terminal after

**B. Install Claude Code**
1. Open PowerShell (right-click Start button → "Terminal" or "PowerShell")
2. Paste this one command:

```powershell
irm https://claude.ai/install.ps1 | iex
```

3. Wait for it to finish
4. Close the terminal and open a new one
5. Type `claude --version` — you should see a version number

**C. Log in to Claude Code**
1. In the terminal, type: `claude`
2. It opens your browser — sign in with your Claude account
3. Authorize it
4. Done — you're in Claude Code

---

## Step 3: Set up your project

**A. Create the project folder**
```powershell
mkdir C:\Projects\ceylonvest-pulse
cd C:\Projects\ceylonvest-pulse
```

**B. Initialize git (important for tracking changes)**
```powershell
git init
```

**C. Extract the starter code**
- Take the `ceylonvest-pulse.tar.gz` file I gave you
- Extract it into `C:\Projects\ceylonvest-pulse\`
- You should see: `bot/`, `services/`, `utils/`, `data/`, `requirements.txt`, etc.

**D. Install Python dependencies**
```powershell
pip install -r requirements.txt
```

**E. Set up your .env file**
```powershell
copy .env.example .env
```
Then edit `.env` and paste in your real tokens:
```
TELEGRAM_BOT_TOKEN=your_actual_bot_token_from_botfather
ANTHROPIC_API_KEY=sk-ant-your_actual_api_key
```

---

## Step 4: Create the CLAUDE.md file

This is the most important file. It tells Claude Code exactly what this project is and how to work on it. Create a file called `CLAUDE.md` in your project root.

**In your terminal (inside the project folder):**
```powershell
claude
```

Then say to Claude Code:

```
Read the CLAUDE.md file in this project and familiarize yourself with it. Then help me get the bot running.
```

I've already created the CLAUDE.md for you — see the next file.

---

## Step 5: Add MCP plugins (optional but powerful)

MCP plugins give Claude Code access to external services. In your terminal:

**GitHub (for pushing code):**
```bash
claude mcp add github -- npx -y @modelcontextprotocol/server-github
```

**File system (already built-in, but for extra access):**
```bash
claude mcp add filesystem -- npx -y @anthropic-ai/mcp-server-filesystem /path/to/project
```

---

## Step 6: Start building with Claude Code

Once you're in Claude Code with the project open, here's how to talk to it:

**First session — get the bot running:**
```
I need to get the CeylonVest Pulse Telegram bot running. 
Read the CLAUDE.md file for full project context.
Let's start by testing the CSE API connection, then run the bot.
```

**Adding the news scraper:**
```
Build the RSS news scraper for Daily FT and EconomyNext. 
It should extract ticker mentions, score sentiment via Claude API, 
and store results in the SQLite database.
Follow the patterns in services/pulse_db.py for data storage.
```

**Adding the X/Twitter monitor:**
```
Build the X/Twitter scraper that monitors CSE-related keywords 
and hashtags. Extract ticker mentions and feed them into the 
sentiment pipeline. Use ntscraper or similar.
```

**Adding the FB group scraper:**
```
Set up Apify integration to scrape the top 5 public CSE Facebook 
groups every 30 minutes. Extract posts and comments, run them 
through the ticker extractor, and store in pulse_db.
```

**Deploying to Railway:**
```
Help me deploy this bot to Railway so it runs 24/7. 
Set up the Procfile, environment variables, and cron scheduling 
for the scrapers.
```

---

## Tips for working with Claude Code

1. **Always start sessions with context**: "Read CLAUDE.md" should be your first instruction in any new session

2. **Be specific about what you want**: Instead of "make it better", say "add error handling to the CSE API calls in services/cse_api.py that retries 3 times with exponential backoff"

3. **Use Plan Mode for big changes**: Type `/plan` before complex tasks — Claude Code will show you what it plans to do before making changes

4. **Commit often**: After each working feature, tell Claude Code to commit: "Commit this with message: add RSS news scraper"

5. **Test as you go**: "Run the bot locally and test with KPHL ticker" — Claude Code can execute commands and show you the output

6. **When stuck**: "Run claude doctor" in your terminal to diagnose issues
