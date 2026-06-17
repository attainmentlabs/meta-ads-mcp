# Meta Ads AI Connectors Parity Roadmap

This repo is the independent open source Meta Ads MCP. Meta now has the official Ads AI Connectors path. The goal is to keep the independent version useful for operators who want control, auditability, and a forkable workflow.

## Shipped in this track

- Broader read tools: account summary, campaigns, ad sets, ads.
- Reporting: insights by account, campaign, ad set, or ad.
- Media: image upload tool.
- Budget control: daily budget update tool.
- Bulk operations: campaign status updates across many campaign IDs.
- Safety: dry-run defaults, confirmation gates, daily budget cap, audit log.

## Next parity layer

| Capability | Status | Notes |
|---|---|---|
| Hosted MCP endpoint | Planned | Streamable HTTP server for remote MCP clients. |
| OAuth login | Planned | Replace manual token setup with Meta OAuth flow. |
| One-click Claude setup | Planned | Generate a Claude-ready config block and validate connection. |
| One-click ChatGPT setup | Planned | Document connector flow after hosted MCP exists. |
| One-click Cursor setup | Planned | Generate Cursor MCP config and validation prompt. |
| One-click Codex setup | Planned | Generate Codex MCP config and validation prompt. |
| More API coverage | Planned | Add pages, pixels, custom audiences, catalog, creative library, previews, recommendations, and rules. |
| Approval workflow UI | Planned | Lightweight web approval page before live writes. |

## Non-copyable Meta advantages

- First-party Meta trust.
- Meta-hosted OAuth brand trust.
- Official platform support.
- Direct Meta roadmap access.

## Positioning

Meta is the institutional path. This project is the operator path: inspectable, forkable, self-managed, and conservative by default.
