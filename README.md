# meta-ads-mcp

MCP server for creating and managing Meta (Facebook/Instagram) ad campaigns directly from Claude. Tell Claude what you want. It deploys.

Built by [Attainment Labs](https://www.attainmentlabs.com).

---

## What it does

Add this server to your Claude config. You get 5 tools:

| Tool | What it does |
|------|-------------|
| `create_meta_campaign` | Create a full campaign: campaign, ad set, creatives, and ads |
| `get_campaign_status` | Check status of a campaign, its ad sets, and ads |
| `pause_campaign` | Pause a live campaign |
| `activate_campaign` | Activate a paused campaign |
| `delete_campaign` | Permanently delete a campaign |

All campaigns are created as **PAUSED** by default. You review before spending.

---

## Install

### Option 1: uvx (recommended, no install needed)

```bash
# No setup required — uvx runs it directly
```

Add to `~/.mcp.json`:

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "uvx",
      "args": ["meta-ads-mcp @ git+https://github.com/attainmentlabs/meta-ads-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "your-token-here",
        "META_AD_ACCOUNT_ID": "your-account-id",
        "META_PAGE_ID": "your-page-id"
      }
    }
  }
}
```

### Option 2: pip install

```bash
pip install "meta-ads-mcp @ git+https://github.com/attainmentlabs/meta-ads-mcp"
```

Then in `~/.mcp.json`:

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "meta-ads-mcp",
      "env": {
        "META_ACCESS_TOKEN": "your-token-here",
        "META_AD_ACCOUNT_ID": "your-account-id",
        "META_PAGE_ID": "your-page-id"
      }
    }
  }
}
```

---

## Credentials

You need three values from your Meta Business Manager:

| Variable | Where to find it |
|----------|-----------------|
| `META_ACCESS_TOKEN` | Meta for Developers: Graph API Explorer, generate a long-lived token with `ads_management` permission |
| `META_AD_ACCOUNT_ID` | Meta Business Manager: Settings > Ad Accounts (numbers only, no `act_` prefix) |
| `META_PAGE_ID` | Facebook Page: Settings > Page Info > Page ID |

The access token expires. Generate a 60-day long-lived token to reduce rotation frequency.

---

## Usage examples

Once the server is connected, just describe what you want:

**Create a campaign:**
> "Create a Meta campaign targeting US fitness enthusiasts aged 25-40. Daily budget $30. Use the image at /Users/me/ads/hero.jpg. Copy: 'Track every rep. Hit every goal.' Headline: 'FitCommit AI'. CTA: Learn More. Link to fitcommit.ai."

**Check status:**
> "What's the status of campaign 120243616427570285?"

**Pause:**
> "Pause campaign 120243616427570285."

**Activate:**
> "Go live with campaign 120243616427570285."

**Delete:**
> "Delete campaign 120243616427570285."

---

## dry_run mode

`create_meta_campaign` defaults to `dry_run=True`. This simulates all API calls and returns fake IDs without making any requests or spending money. Set `dry_run=False` when you're ready to deploy.

---

## YAML workflow

Prefer writing campaigns as config files? Use [meta-ads-cli](https://github.com/attainmentlabs/meta-ads-cli) — the companion CLI tool.

---

## Requirements

- Python 3.9+
- `uv` for the uvx install path
- A Meta Business Manager account with an ad account and Facebook Page

---

## License

MIT
