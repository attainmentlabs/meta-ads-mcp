# Meta Credentials Setup Guide

This guide gets you the three values needed to run meta-ads-mcp:

- `META_ACCESS_TOKEN`
- `META_AD_ACCOUNT_ID`
- `META_PAGE_ID`

---

## Before you start

You need:
- A Facebook account
- A Facebook Page (the one your ads will run from)
- A Meta Business Manager account with an Ad Account

If you don't have Business Manager: go to **business.facebook.com**, click "Create Account", and follow the prompts. Takes about 5 minutes.

---

## Step 1: Create a Facebook App

1. Go to **developers.facebook.com**
2. Click **My Apps** (top right) → **Create App**
3. When asked "What do you want your app to do?", select **Other** → click **Next**
4. For app type, select **Business** → click **Next**
5. Give it a name (e.g. "Meta Ads MCP") — this is just for your reference
6. Under "Business portfolio", select your Business Manager account
7. Click **Create App**

You'll land on the App Dashboard.

---

## Step 2: Add the Marketing API

1. On the App Dashboard, scroll down to **Add Products to Your App**
2. Find **Marketing API** and click **Set Up**
3. You'll see a "Marketing API" section appear in the left sidebar

That's all — no further configuration needed here.

---

## Step 3: Generate an Access Token

1. Go to **developers.facebook.com/tools/explorer**
2. In the top-right dropdown, select the app you just created (e.g. "Meta Ads MCP")
3. Click the **Generate Access Token** button
4. A permissions dialog will appear. Add these permissions:
   - `ads_management`
   - `ads_read`
   - `pages_read_engagement`
   - `pages_show_list`
5. Click **Generate Access Token** → click through the Facebook login/authorization dialogs
6. Copy the token that appears in the "Access Token" field — this is your short-lived token (valid ~1 hour)

---

## Step 4: Convert to a Long-Lived Token (60 days)

Short-lived tokens expire in an hour. Exchange it for a 60-day token.

1. Still in Graph API Explorer, find your **App ID** and **App Secret**:
   - Go back to the App Dashboard → **App Settings** → **Basic**
   - Copy the App ID and App Secret (click "Show" to reveal the secret)

2. In Graph API Explorer, paste this into the URL field and click Submit:

```
GET /oauth/access_token?grant_type=fb_exchange_token&client_id={YOUR_APP_ID}&client_secret={YOUR_APP_SECRET}&fb_exchange_token={YOUR_SHORT_LIVED_TOKEN}
```

Replace `{YOUR_APP_ID}`, `{YOUR_APP_SECRET}`, and `{YOUR_SHORT_LIVED_TOKEN}` with the real values.

3. The response will contain an `access_token` field — this is your **long-lived token**. Copy it.

This is your `META_ACCESS_TOKEN`. It lasts 60 days. After that, repeat Steps 3-4 to get a new one.

---

## Step 5: Find Your Ad Account ID

1. Go to **business.facebook.com**
2. Click the grid icon (top left) → **Ad Accounts**
3. You'll see your ad account(s) listed with IDs like `act_123456789`
4. Copy the numbers only — **no `act_` prefix**

Example: if you see `act_123456789`, your `META_AD_ACCOUNT_ID` is `123456789`.

---

## Step 6: Find Your Page ID

1. Go to your Facebook Page
2. Click **About** in the left sidebar
3. Scroll down to **Page transparency** — your Page ID is listed there

Alternatively:
- Go to the page, click the three dots (**...**) → **About** → scroll to find the numeric Page ID

---

## You now have all three values

| Variable | What you collected |
|----------|--------------------|
| `META_ACCESS_TOKEN` | The long-lived token from Step 4 |
| `META_AD_ACCOUNT_ID` | The numbers-only ID from Step 5 |
| `META_PAGE_ID` | The numeric Page ID from Step 6 |

---

## Step 7: Add to ~/.mcp.json

Open `~/.mcp.json` (create it if it doesn't exist) and add:

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "uvx",
      "args": ["meta-ads-manager-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "paste-your-token-here",
        "META_AD_ACCOUNT_ID": "paste-your-account-id-here",
        "META_PAGE_ID": "paste-your-page-id-here"
      }
    }
  }
}
```

If `~/.mcp.json` already has other servers, add the `"meta-ads"` block inside the existing `"mcpServers"` object.

---

## Step 8: Restart Claude

Close and reopen Claude Code. Run `/mcp` to confirm the `meta-ads` server appears with 5 tools.

---

## Troubleshooting

**"Invalid OAuth access token"**
Token expired or has wrong permissions. Repeat Steps 3-4 and make sure you added `ads_management` in the permissions dialog.

**"Ad account not found"**
Double-check you're using numbers only (no `act_` prefix) and the account is connected to the same Business Manager as your app.

**"Page not found"**
Confirm the Page is connected to your Business Manager: business.facebook.com → Pages → verify it's listed.

**Token expired after 60 days**
Repeat Steps 3-4. Consider setting a calendar reminder 55 days out.
