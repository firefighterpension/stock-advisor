# Use Investment Advisor like an app

## A. On your computer (double-click)

1. Install Python 3.10 or newer from python.org. On Windows, tick "Add Python to PATH".
2. Unzip this folder.
3. Windows: double-click `run.bat`. Mac: double-click `run.command`
   (if it won't open, right-click > Open once, or run `chmod +x run.command`).
4. The first run installs what it needs (about a minute). Your browser then opens the app.
5. Close the black terminal window to stop it.

For written reports, either paste your Anthropic key under Settings in the app,
or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add it.

## B. Online, on your phone and computer (free)

1. Create a free account at github.com and make a **private** repository.
2. Upload everything in this folder to it. The `.gitignore` already keeps secrets out.
3. Go to share.streamlit.io and sign in with GitHub.
4. Choose New app, pick your repository, set the main file to `app.py`, and deploy.
   It takes a few minutes and gives you a web link.
5. Add your key: App settings > Secrets, then paste:
   `ANTHROPIC_API_KEY = "sk-ant-..."`
6. Make it private: App settings > Sharing, and allow only your own email.
   Without this, anyone with the link can use your API key's credits.

### Put it on your phone's home screen

- iPhone (Safari): Share button > Add to Home Screen.
- Android (Chrome): menu (three dots) > Add to Home screen or Install app.

It then opens full screen like an app.

## Good to know

- Free Streamlit apps go to sleep after a few days without visits. Open the link and
  tap the wake-up button; it restarts in under a minute.
- Yahoo Finance sometimes rate-limits cloud servers. If you see data errors online
  but not on your computer, wait a few minutes or ask for a paid data source to be added.
- Your portfolio entries are not saved between visits yet.
