"""MCP server for Meta (Facebook/Instagram) ad campaign management."""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("meta-ads")


# ---------------------------------------------------------------------------
# Meta API client (self-contained, no click dependency)
# ---------------------------------------------------------------------------

class MetaAPIError(Exception):
    """Raised when the Meta API returns an error."""

    def __init__(self, status_code, message, error_code=None):
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class MetaAdsAPI:
    """Lightweight wrapper around the Meta Marketing API."""

    def __init__(self, access_token, ad_account_id, page_id, api_version="v21.0", dry_run=False):
        self.access_token = access_token
        self.ad_account_id = ad_account_id
        self.act_id = f"act_{ad_account_id}"
        self.page_id = page_id
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{api_version}"
        self.dry_run = dry_run
        self._dry_run_counter = 0

    def _request(self, method, endpoint, **kwargs):
        """Make an API request to the Meta Graph API."""
        url = f"{self.base_url}/{endpoint}"
        kwargs.setdefault("params", {})
        kwargs["params"]["access_token"] = self.access_token

        if self.dry_run:
            self._dry_run_counter += 1
            fake_id = f"dry_run_{self._dry_run_counter}"
            params = {k: v for k, v in kwargs.get("params", {}).items() if k != "access_token"}
            print(f"[DRY RUN] {method} {endpoint}", file=sys.stderr)
            if params:
                preview = json.dumps(params, indent=2)
                if len(preview) > 500:
                    preview = preview[:500] + "..."
                print(f"  Params: {preview}", file=sys.stderr)
            return {"id": fake_id}

        resp = getattr(requests, method.lower())(url, **kwargs)

        if resp.status_code != 200:
            try:
                error_data = resp.json().get("error", {})
                message = error_data.get("message", resp.text)
                error_code = error_data.get("code")
            except Exception:
                message = resp.text
                error_code = None
            raise MetaAPIError(resp.status_code, message, error_code)

        return resp.json()

    def upload_image(self, image_path):
        """Upload an ad image. Returns the image hash."""
        from pathlib import Path
        path = Path(image_path)
        with open(path, "rb") as f:
            result = self._request(
                "POST",
                f"{self.act_id}/adimages",
                files={"filename": (path.name, f, "image/png")},
            )
        if self.dry_run:
            return "dry_run_hash"
        images = result.get("images", {})
        for key, val in images.items():
            return val.get("hash")
        raise MetaAPIError(0, f"Unexpected image upload response: {result}")

    def create_campaign(self, name, objective="OUTCOME_TRAFFIC", status="PAUSED", special_ad_categories=None):
        """Create an ad campaign. Returns the campaign ID."""
        result = self._request(
            "POST",
            f"{self.act_id}/campaigns",
            params={
                "name": name,
                "objective": objective,
                "status": status,
                "special_ad_categories": json.dumps(special_ad_categories or []),
                "is_adset_budget_sharing_enabled": "false",
            },
        )
        return result.get("id", "dry_run_id")

    def create_ad_set(self, name, campaign_id, daily_budget, targeting,
                      optimization_goal="LINK_CLICKS", billing_event="IMPRESSIONS",
                      bid_strategy="LOWEST_COST_WITHOUT_CAP", status="PAUSED"):
        """Create an ad set with targeting. Returns the ad set ID."""
        _check_daily_budget_limit(daily_budget, "create_ad_set")
        targeting_spec = {
            "age_min": targeting.get("age_min", 18),
            "age_max": targeting.get("age_max", 65),
            "genders": targeting.get("genders", [0]),
            "geo_locations": {
                "countries": targeting.get("countries", ["US"]),
            },
        }
        if targeting.get("interests"):
            targeting_spec["flexible_spec"] = [
                {"interests": targeting["interests"]}
            ]
        platforms = targeting.get("platforms", ["facebook", "instagram"])
        targeting_spec["publisher_platforms"] = platforms
        if "facebook" in platforms:
            targeting_spec["facebook_positions"] = targeting.get("facebook_positions", ["feed"])
        if "instagram" in platforms:
            targeting_spec["instagram_positions"] = targeting.get(
                "instagram_positions", ["stream", "story", "reels"]
            )
        result = self._request(
            "POST",
            f"{self.act_id}/adsets",
            params={
                "name": name,
                "campaign_id": campaign_id,
                "daily_budget": str(daily_budget),
                "billing_event": billing_event,
                "optimization_goal": optimization_goal,
                "bid_strategy": bid_strategy,
                "status": status,
                "targeting": json.dumps(targeting_spec),
            },
        )
        return result.get("id", "dry_run_id")

    def create_ad_creative(self, name, image_hash, primary_text, headline, description, link, cta="LEARN_MORE"):
        """Create an ad creative. Returns the creative ID."""
        result = self._request(
            "POST",
            f"{self.act_id}/adcreatives",
            params={
                "name": name,
                "object_story_spec": json.dumps({
                    "link_data": {
                        "image_hash": image_hash,
                        "link": link,
                        "message": primary_text,
                        "name": headline,
                        "description": description,
                        "call_to_action": {
                            "type": cta,
                            "value": {"link": link},
                        },
                    },
                    "page_id": self.page_id,
                }),
            },
        )
        return result.get("id", "dry_run_id")

    def create_ad(self, name, ad_set_id, creative_id, status="PAUSED"):
        """Create an ad. Returns the ad ID."""
        result = self._request(
            "POST",
            f"{self.act_id}/ads",
            params={
                "name": name,
                "adset_id": ad_set_id,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": status,
            },
        )
        return result.get("id", "dry_run_id")

    def get_campaign(self, campaign_id, fields="name,status,objective,daily_budget"):
        """Get campaign details."""
        return self._request("GET", campaign_id, params={"fields": fields})

    def get_ad_account(self, fields="id,name,account_status,currency,timezone_name,amount_spent,balance"):
        """Get configured ad account details."""
        return self._request("GET", self.act_id, params={"fields": fields})

    def list_campaigns(self, fields="id,name,status,effective_status,objective,created_time,updated_time", limit=25):
        """List campaigns in the configured ad account."""
        result = self._request(
            "GET",
            f"{self.act_id}/campaigns",
            params={"fields": fields, "limit": str(limit)},
        )
        return result.get("data", [])

    def list_ad_sets(self, fields="id,name,status,effective_status,daily_budget,campaign_id", limit=25):
        """List ad sets in the configured ad account."""
        result = self._request(
            "GET",
            f"{self.act_id}/adsets",
            params={"fields": fields, "limit": str(limit)},
        )
        return result.get("data", [])

    def list_ads(self, fields="id,name,status,effective_status,adset_id,campaign_id", limit=25):
        """List ads in the configured ad account."""
        result = self._request(
            "GET",
            f"{self.act_id}/ads",
            params={"fields": fields, "limit": str(limit)},
        )
        return result.get("data", [])

    def get_ad_sets(self, campaign_id, fields="name,status,daily_budget"):
        """Get ad sets for a campaign."""
        result = self._request("GET", f"{campaign_id}/adsets", params={"fields": fields})
        return result.get("data", [])

    def get_ads(self, campaign_id, fields="name,status,effective_status"):
        """Get ads for a campaign."""
        result = self._request("GET", f"{campaign_id}/ads", params={"fields": fields})
        return result.get("data", [])

    def get_insights(
        self,
        object_id,
        fields="impressions,clicks,spend,cpc,cpm,ctr,actions",
        level=None,
        date_preset="last_7d",
        limit=25,
    ):
        """Get insights for an account, campaign, ad set, or ad."""
        params = {
            "fields": fields,
            "date_preset": date_preset,
            "limit": str(limit),
        }
        if level:
            params["level"] = level
        result = self._request("GET", f"{object_id}/insights", params=params)
        return result.get("data", [])

    def update_status(self, object_id, status):
        """Update the status of a campaign, ad set, or ad."""
        return self._request("POST", object_id, params={"status": status})

    def update_daily_budget(self, object_id, daily_budget_cents):
        """Update daily budget for a campaign or ad set."""
        _check_daily_budget_limit(daily_budget_cents, "update_daily_budget")
        return self._request(
            "POST",
            object_id,
            params={"daily_budget": str(daily_budget_cents)},
        )

    def delete_campaign(self, campaign_id):
        """Delete a campaign (sets status to DELETED)."""
        return self.update_status(campaign_id, "DELETED")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_api(dry_run: bool = False) -> MetaAdsAPI:
    return MetaAdsAPI(
        access_token=os.environ["META_ACCESS_TOKEN"],
        ad_account_id=os.environ["META_AD_ACCOUNT_ID"],
        page_id=os.environ["META_PAGE_ID"],
        api_version=os.environ.get("META_API_VERSION", "v21.0"),
        dry_run=dry_run,
    )


def _audit_log_path() -> Path:
    configured = os.environ.get("META_ADS_AUDIT_LOG_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".meta-ads-mcp" / "audit.jsonl"


def _write_audit(action: str, request: dict, result: dict) -> None:
    """Write a local audit event without credentials or secrets."""
    path = _audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "ad_account_id": os.environ.get("META_AD_ACCOUNT_ID"),
        "request": request,
        "result": result,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def _require_confirmation(confirm: bool, action: str) -> None:
    if not confirm:
        raise ValueError(
            f"{action} changes a live Meta ad account. Re-run with confirm=True after reviewing the plan."
        )


def _check_daily_budget_limit(daily_budget_cents: int, action: str) -> None:
    if daily_budget_cents <= 0:
        raise ValueError(f"{action} daily_budget_cents must be positive.")
    raw_limit = os.environ.get("META_ADS_MAX_DAILY_BUDGET_CENTS")
    if not raw_limit:
        return
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ValueError("META_ADS_MAX_DAILY_BUDGET_CENTS must be an integer.") from exc
    if daily_budget_cents > limit:
        raise ValueError(
            f"{action} budget {daily_budget_cents} exceeds META_ADS_MAX_DAILY_BUDGET_CENTS={limit}."
        )


def _bounded_limit(limit: int) -> int:
    if limit < 1:
        return 1
    if limit > 100:
        return 100
    return limit


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def create_meta_campaign(
    campaign_name: str,
    ad_set_name: str,
    objective: str = "OUTCOME_TRAFFIC",
    countries: list = ["US"],
    age_min: int = 18,
    age_max: int = 65,
    daily_budget_cents: int = 1000,
    optimization_goal: str = "LINK_CLICKS",
    ads: list = [],
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Create a complete Meta ad campaign: campaign, ad set, creatives, and ads.

    Each item in `ads` is a dict with:
      - name (str): ad name
      - image_path (str): absolute path to image file on disk
      - primary_text (str): ad body copy
      - headline (str): ad headline
      - link (str): destination URL
      - cta (str, optional): call-to-action button, default "LEARN_MORE"
      - description (str, optional): ad description text

    daily_budget_cents: budget in cents. 1000 = $10/day, 3000 = $30/day.

    dry_run: when True (default), simulates all API calls without spending money.
    Set dry_run=False to actually deploy. All campaigns start as PAUSED regardless.
    confirm: required when dry_run=False. This is the approval gate.

    Valid objectives: OUTCOME_TRAFFIC, OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT,
    OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_APP_PROMOTION

    Valid CTAs: LEARN_MORE, SIGN_UP, DOWNLOAD, SHOP_NOW, BOOK_NOW, GET_OFFER,
    SUBSCRIBE, CONTACT_US, APPLY_NOW, WATCH_MORE, INSTALL_MOBILE_APP
    """
    if not dry_run:
        _require_confirmation(confirm, "create_meta_campaign")
    api = _get_api(dry_run=dry_run)

    targeting = {
        "countries": countries,
        "age_min": age_min,
        "age_max": age_max,
    }

    result = {
        "dry_run": dry_run,
        "confirmed": confirm,
        "campaign_id": None,
        "ad_set_id": None,
        "creatives": [],
        "ads": [],
    }

    # Upload images
    image_hashes = {}
    for ad in ads:
        image_hashes[ad["name"]] = api.upload_image(ad["image_path"])

    # Create campaign
    campaign_id = api.create_campaign(
        name=campaign_name,
        objective=objective,
        status="PAUSED",
    )
    result["campaign_id"] = campaign_id

    # Create ad set
    ad_set_id = api.create_ad_set(
        name=ad_set_name,
        campaign_id=campaign_id,
        daily_budget=daily_budget_cents,
        targeting=targeting,
        optimization_goal=optimization_goal,
        status="PAUSED",
    )
    result["ad_set_id"] = ad_set_id

    # Create creatives and ads
    for ad in ads:
        creative_id = api.create_ad_creative(
            name=f"{ad['name']} - Creative",
            image_hash=image_hashes[ad["name"]],
            primary_text=ad["primary_text"].strip(),
            headline=ad.get("headline", ""),
            description=ad.get("description", ""),
            link=ad["link"],
            cta=ad.get("cta", "LEARN_MORE"),
        )
        result["creatives"].append(creative_id)

        ad_id = api.create_ad(
            name=ad["name"],
            ad_set_id=ad_set_id,
            creative_id=creative_id,
            status="PAUSED",
        )
        result["ads"].append(ad_id)

    _write_audit(
        "create_meta_campaign",
        {
            "campaign_name": campaign_name,
            "ad_set_name": ad_set_name,
            "objective": objective,
            "countries": countries,
            "age_min": age_min,
            "age_max": age_max,
            "daily_budget_cents": daily_budget_cents,
            "optimization_goal": optimization_goal,
            "ad_count": len(ads),
            "dry_run": dry_run,
            "confirmed": confirm,
        },
        result,
    )
    return result


@mcp.tool()
def get_ad_account_summary() -> dict:
    """Get the configured Meta ad account summary.

    Read-only. Use this before campaign work to confirm the connected account,
    currency, timezone, spend, balance, and account status.
    """
    api = _get_api()
    account = api.get_ad_account()
    return {
        "id": account.get("id"),
        "name": account.get("name"),
        "account_status": account.get("account_status"),
        "currency": account.get("currency"),
        "timezone_name": account.get("timezone_name"),
        "amount_spent": account.get("amount_spent"),
        "balance": account.get("balance"),
    }


@mcp.tool()
def list_campaigns(limit: int = 25) -> dict:
    """List recent campaigns in the configured Meta ad account.

    Read-only. Use this to find campaign IDs before status, insights, budget,
    pause, activate, or bulk operations.
    """
    api = _get_api()
    campaigns = api.list_campaigns(limit=_bounded_limit(limit))
    return {"campaigns": campaigns, "count": len(campaigns)}


@mcp.tool()
def list_ad_sets(limit: int = 25) -> dict:
    """List recent ad sets in the configured Meta ad account.

    Read-only. Use this to find ad set IDs before budget or status changes.
    """
    api = _get_api()
    ad_sets = api.list_ad_sets(limit=_bounded_limit(limit))
    return {"ad_sets": ad_sets, "count": len(ad_sets)}


@mcp.tool()
def list_ads(limit: int = 25) -> dict:
    """List recent ads in the configured Meta ad account.

    Read-only. Use this to find ad IDs and inspect delivery status.
    """
    api = _get_api()
    ads = api.list_ads(limit=_bounded_limit(limit))
    return {"ads": ads, "count": len(ads)}


@mcp.tool()
def get_meta_insights(
    object_id: str = "",
    level: str = "",
    date_preset: str = "last_7d",
    limit: int = 25,
) -> dict:
    """Get Meta Ads performance insights.

    Read-only. object_id can be an ad account, campaign, ad set, or ad ID.
    Leave object_id blank to use the configured ad account. Use level for
    account breakdowns such as campaign, adset, or ad.
    """
    api = _get_api()
    target = object_id or api.act_id
    insights = api.get_insights(
        object_id=target,
        level=level or None,
        date_preset=date_preset,
        limit=_bounded_limit(limit),
    )
    return {
        "object_id": target,
        "level": level or None,
        "date_preset": date_preset,
        "insights": insights,
        "count": len(insights),
    }


@mcp.tool()
def upload_ad_image(image_path: str, dry_run: bool = True, confirm: bool = False) -> dict:
    """Upload an image to the configured Meta ad account.

    dry_run defaults to True. Set dry_run=False and confirm=True to upload.
    Returns an image hash that can be used in ad creatives.
    """
    if not dry_run:
        _require_confirmation(confirm, "upload_ad_image")
    api = _get_api(dry_run=dry_run)
    image_hash = api.upload_image(image_path)
    result = {"dry_run": dry_run, "confirmed": confirm, "image_hash": image_hash}
    _write_audit(
        "upload_ad_image",
        {"image_path": image_path, "dry_run": dry_run, "confirmed": confirm},
        result,
    )
    return result


@mcp.tool()
def update_daily_budget(
    object_id: str,
    daily_budget_cents: int,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Update daily budget for a campaign or ad set.

    dry_run defaults to True. Set dry_run=False and confirm=True after review.
    If META_ADS_MAX_DAILY_BUDGET_CENTS is set, the budget cannot exceed it.
    """
    if not dry_run:
        _require_confirmation(confirm, "update_daily_budget")
    api = _get_api(dry_run=dry_run)
    api.update_daily_budget(object_id, daily_budget_cents)
    result = {
        "success": True,
        "object_id": object_id,
        "daily_budget_cents": daily_budget_cents,
        "dry_run": dry_run,
        "confirmed": confirm,
    }
    _write_audit(
        "update_daily_budget",
        {
            "object_id": object_id,
            "daily_budget_cents": daily_budget_cents,
            "dry_run": dry_run,
            "confirmed": confirm,
        },
        result,
    )
    return result


@mcp.tool()
def bulk_update_campaign_status(
    campaign_ids: list,
    status: str,
    dry_run: bool = True,
    confirm: bool = False,
) -> dict:
    """Bulk pause, activate, or delete campaigns.

    status must be PAUSED, ACTIVE, or DELETED. dry_run defaults to True.
    Set dry_run=False and confirm=True after reviewing the campaign IDs.
    """
    status = status.upper()
    if status not in {"PAUSED", "ACTIVE", "DELETED"}:
        raise ValueError("status must be PAUSED, ACTIVE, or DELETED.")
    if not dry_run:
        _require_confirmation(confirm, "bulk_update_campaign_status")
    api = _get_api(dry_run=dry_run)
    changed = []
    for campaign_id in campaign_ids:
        api.update_status(campaign_id, status)
        changed.append({"campaign_id": campaign_id, "status": status})
    result = {
        "success": True,
        "dry_run": dry_run,
        "confirmed": confirm,
        "changed": changed,
        "count": len(changed),
    }
    _write_audit(
        "bulk_update_campaign_status",
        {
            "campaign_ids": campaign_ids,
            "status": status,
            "dry_run": dry_run,
            "confirmed": confirm,
        },
        result,
    )
    return result


@mcp.tool()
def get_campaign_status(campaign_id: str) -> dict:
    """Get the status of a Meta campaign including its ad sets and ads.

    Returns campaign name, status, objective, and lists of ad sets and ads
    with their statuses and budgets.
    """
    api = _get_api()
    campaign = api.get_campaign(campaign_id, fields="id,name,status,objective,daily_budget")
    ad_sets = api.get_ad_sets(campaign_id, fields="id,name,status,daily_budget")
    ads = api.get_ads(campaign_id, fields="id,name,status,effective_status")

    return {
        "campaign": {
            "id": campaign.get("id"),
            "name": campaign.get("name"),
            "status": campaign.get("status"),
            "objective": campaign.get("objective"),
        },
        "ad_sets": [
            {
                "id": s.get("id"),
                "name": s.get("name"),
                "status": s.get("status"),
                "daily_budget_cents": s.get("daily_budget"),
            }
            for s in ad_sets
        ],
        "ads": [
            {
                "id": a.get("id"),
                "name": a.get("name"),
                "status": a.get("status"),
                "effective_status": a.get("effective_status"),
            }
            for a in ads
        ],
    }


@mcp.tool()
def pause_campaign(campaign_id: str) -> dict:
    """Pause a live Meta campaign. Safe to call on already-paused campaigns."""
    api = _get_api()
    api.update_status(campaign_id, "PAUSED")
    result = {"success": True, "campaign_id": campaign_id, "status": "PAUSED"}
    _write_audit("pause_campaign", {"campaign_id": campaign_id}, result)
    return result


@mcp.tool()
def activate_campaign(campaign_id: str, confirm: bool = False) -> dict:
    """Activate (unpause) a Meta campaign. This will resume ad spending.

    The campaign must have a valid payment method and approved creatives.
    Set confirm=True after reviewing the campaign in Ads Manager.
    """
    _require_confirmation(confirm, "activate_campaign")
    api = _get_api()
    api.update_status(campaign_id, "ACTIVE")
    result = {"success": True, "campaign_id": campaign_id, "status": "ACTIVE", "confirmed": confirm}
    _write_audit("activate_campaign", {"campaign_id": campaign_id, "confirmed": confirm}, result)
    return result


@mcp.tool()
def delete_campaign(campaign_id: str, confirm: bool = False) -> dict:
    """Permanently delete a Meta campaign. This cannot be undone.

    Set confirm=True after reviewing the campaign ID.
    """
    _require_confirmation(confirm, "delete_campaign")
    api = _get_api()
    api.delete_campaign(campaign_id)
    result = {"success": True, "campaign_id": campaign_id, "status": "DELETED", "confirmed": confirm}
    _write_audit("delete_campaign", {"campaign_id": campaign_id, "confirmed": confirm}, result)
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
