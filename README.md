# meta-ads-manager-mcp

MCP server for creating and managing Meta (Facebook/Instagram) ad campaigns directly from Claude. Tell Claude what you want. It deploys.

Built by [Attainment Labs](https://www.attainmentlabs.com).

---

## Status in the Meta Ads ecosystem

This is an early independent open source Meta Ads MCP server, first published in February 2026 before Meta later introduced its official Ads AI Connectors and hosted Ads MCP endpoint.

Use Meta's official connector if you want Meta-hosted OAuth and first-party support. Use this project if you want a lightweight, self-managed MCP server that you can inspect, fork, and run with your own Meta app credentials.

Related:

- [Meta's official Ads CLI documentation](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/ads-cli-overview)
- [Attainment's companion CLI](https://github.com/attainmentlabs/meta-ads-cli)
- [Meta Ads Automation Playbook](https://attainmentlabs.com/meta-ads-playbook)

---

## What it does

Add this server to your Claude config. You get campaign creation, reporting, bulk operations, budget control, and safety tools:

| Tool | What it does |
|------|-------------|
| `create_meta_campaign` | Create a full campaign: campaign, ad set, creatives, and ads |
| `get_ad_account_summary` | Confirm connected ad account, currency, timezone, spend, balance, and status |
| `list_campaigns` | List recent campaigns in the configured ad account |
| `list_ad_sets` | List recent ad sets in the configured ad account |
| `list_ads` | List recent ads in the configured ad account |
| `get_campaign_status` | Check status of a campaign, its ad sets, and ads |
| `get_meta_insights` | Pull account, campaign, ad set, or ad performance insights |
| `upload_ad_image` | Upload an image and return the image hash for creatives |
| `update_daily_budget` | Update campaign or ad set daily budget |
| `bulk_update_campaign_status` | Bulk pause, activate, or delete campaigns |
| `pause_campaign` | Pause a live campaign |
| `activate_campaign` | Activate a paused campaign |
| `delete_campaign` | Permanently delete a campaign |

All campaigns are created as **PAUSED** by default. You review before spending.

Safety controls:

- `dry_run=True` by default on campaign creation, media upload, budget updates, and bulk status changes.
- `confirm=True` is required for live campaign creation, uploads, budget updates, activation, deletion, and bulk status changes.
- `META_ADS_MAX_DAILY_BUDGET_CENTS` can cap campaign and ad set daily budgets.
- `META_ADS_AUDIT_LOG_PATH` can set a JSONL audit log path. Default is `~/.meta-ads-mcp/audit.jsonl`.

---

## Install

### Option 1: Let Claude set it up for you (easiest)

If you use [Claude Code](https://claude.ai/download), paste this prompt:

> "Set up meta-ads-mcp for me: https://github.com/attainmentlabs/meta-ads-mcp"

Claude will check your environment, walk you through getting your Meta credentials step by step, edit your `~/.mcp.json`, and confirm when it's done. No docs to read.

---

### Option 2: uvx (recommended, no install needed)

```bash
# No setup required. uvx runs it directly
```

Add to `~/.mcp.json`:

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "uvx",
      "args": ["meta-ads-manager-mcp"],
      "env": {
        "META_ACCESS_TOKEN": "your-token-here",
        "META_AD_ACCOUNT_ID": "your-account-id",
        "META_PAGE_ID": "your-page-id",
        "META_ADS_MAX_DAILY_BUDGET_CENTS": "5000"
      }
    }
  }
}
```

### Option 2: pip install

```bash
pip install meta-ads-manager-mcp
```

Then in `~/.mcp.json`:

```json
{
  "mcpServers": {
    "meta-ads": {
      "command": "meta-ads-manager-mcp",
      "env": {
        "META_ACCESS_TOKEN": "your-token-here",
        "META_AD_ACCOUNT_ID": "your-account-id",
        "META_PAGE_ID": "your-page-id",
        "META_ADS_MAX_DAILY_BUDGET_CENTS": "5000"
      }
    }
  }
}
```

---

## Credentials

You need three values from Meta. Full step-by-step walkthrough: **[SETUP.md](SETUP.md)**

| Variable | Where to find it |
|----------|-----------------|
| `META_ACCESS_TOKEN` | Graph API Explorer. Long-lived token with `ads_management` permission |
| `META_AD_ACCOUNT_ID` | Business Manager: Ad Accounts. Numbers only, no `act_` prefix |
| `META_PAGE_ID` | Facebook Page: About → Page transparency → Page ID |
| `META_ADS_MAX_DAILY_BUDGET_CENTS` | Optional daily budget guardrail |
| `META_ADS_AUDIT_LOG_PATH` | Optional JSONL audit log path |

The access token expires after 60 days. See [SETUP.md](SETUP.md) for the exchange flow.

---

## Usage examples

Once the server is connected, just describe what you want:

**Create a campaign:**
> "Create a Meta campaign targeting US fitness enthusiasts aged 25-40. Daily budget $30. Use the image at /Users/me/ads/hero.jpg. Copy: 'Track every rep. Hit every goal.' Headline: 'FitCommit AI'. CTA: Learn More. Link to fitcommit.ai."

**Check status:**
> "What's the status of campaign 120243616427570285?"

**List campaigns:**
> "List my recent Meta campaigns."

**Pull insights:**
> "Show Meta ad account insights for the last 7 days by campaign."

**Update budget safely:**
> "Dry run a budget update to set ad set 120243616427570285 to $30 per day."

**Bulk pause:**
> "Dry run pausing these three campaigns: 111, 222, 333."

**Pause:**
> "Pause campaign 120243616427570285."

**Activate:**
> "Go live with campaign 120243616427570285."

**Delete:**
> "Delete campaign 120243616427570285."

---

## dry_run mode

`create_meta_campaign`, `upload_ad_image`, `update_daily_budget`, and `bulk_update_campaign_status` default to `dry_run=True`. This simulates API calls and returns fake IDs or planned changes without making requests or spending money.

For live changes, set `dry_run=False` and `confirm=True`.

`activate_campaign` and `delete_campaign` also require `confirm=True`.

---

## YAML workflow

Prefer writing campaigns as config files? Use [meta-ads-cli](https://github.com/attainmentlabs/meta-ads-cli), the companion CLI tool.

---

## Requirements

- Python 3.10+
- `uv` for the uvx install path
- A Meta Business Manager account with an ad account and Facebook Page

---

## License

MIT
