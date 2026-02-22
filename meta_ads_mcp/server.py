"""MCP server for Meta (Facebook/Instagram) ad campaign management."""

import json
import os
import sys

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

    def get_ad_sets(self, campaign_id, fields="name,status,daily_budget"):
        """Get ad sets for a campaign."""
        result = self._request("GET", f"{campaign_id}/adsets", params={"fields": fields})
        return result.get("data", [])

    def get_ads(self, campaign_id, fields="name,status,effective_status"):
        """Get ads for a campaign."""
        result = self._request("GET", f"{campaign_id}/ads", params={"fields": fields})
        return result.get("data", [])

    def update_status(self, object_id, status):
        """Update the status of a campaign, ad set, or ad."""
        return self._request("POST", object_id, params={"status": status})

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

    Valid objectives: OUTCOME_TRAFFIC, OUTCOME_AWARENESS, OUTCOME_ENGAGEMENT,
    OUTCOME_LEADS, OUTCOME_SALES, OUTCOME_APP_PROMOTION

    Valid CTAs: LEARN_MORE, SIGN_UP, DOWNLOAD, SHOP_NOW, BOOK_NOW, GET_OFFER,
    SUBSCRIBE, CONTACT_US, APPLY_NOW, WATCH_MORE, INSTALL_MOBILE_APP
    """
    api = _get_api(dry_run=dry_run)

    targeting = {
        "countries": countries,
        "age_min": age_min,
        "age_max": age_max,
    }

    result = {
        "dry_run": dry_run,
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
    return {"success": True, "campaign_id": campaign_id, "status": "PAUSED"}


@mcp.tool()
def activate_campaign(campaign_id: str) -> dict:
    """Activate (unpause) a Meta campaign. This will resume ad spending.

    The campaign must have a valid payment method and approved creatives.
    """
    api = _get_api()
    api.update_status(campaign_id, "ACTIVE")
    return {"success": True, "campaign_id": campaign_id, "status": "ACTIVE"}


@mcp.tool()
def delete_campaign(campaign_id: str) -> dict:
    """Permanently delete a Meta campaign. This cannot be undone."""
    api = _get_api()
    api.delete_campaign(campaign_id)
    return {"success": True, "campaign_id": campaign_id, "status": "DELETED"}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
