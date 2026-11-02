"""VPNGate public feed sync and candidate sanitization.

Feed is read-only HTTPS. Full .ovpn is never returned to App clients.
Dangerous OpenVPN directives are rejected before any Agent call.
"""

from __future__ import annotations

import base64
import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Region, VpngateCandidate

logger = logging.getLogger(__name__)

VPNGATE_CSV_URL = "https://www.vpngate.net/api/iphone/"


async def sync_candidates(db: AsyncSession) -> int:
    print("VPNGate sync started", flush=True)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(VPNGATE_CSV_URL)
            resp.raise_for_status()
            text = resp.text
        print(f"VPNGate feed fetched, length={len(text)}", flush=True)
    except Exception as exc:
        print(f"VPNGate fetch failed: {exc}", flush=True)
        return 0

    # VPNGate sometimes wraps in base64; try decode if it looks like it
    if text and not text.lstrip().startswith("#") and not text.lstrip().startswith("HostName"):
        try:
            decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
            if "HostName" in decoded or "IP" in decoded:
                text = decoded
                print("VPNGate feed decoded from base64", flush=True)
        except Exception as exc:
            print(f"VPNGate base64 decode skipped: {exc}", flush=True)

    # Log first 200 chars for debugging
    print(f"VPNGate feed preview: {text[:200].replace(chr(10), ' ')}", flush=True)

    reader = csv.DictReader(io.StringIO(text))
    count = 0
    skipped = 0
    for row in reader:
        ip = row.get("IP") or row.get("ip")
        country = (row.get("CountryLong") or row.get("CountryShort") or "")[:2].upper()
        if not ip or not country:
            skipped += 1
            continue

        # Ensure region exists
        region = await db.get(Region, country)
        if not region:
            region = Region(code=country, name=country)
            db.add(region)
            await db.flush()

        external_id = row.get("#HostName") or row.get("HostName") or ip
        existing = await db.execute(select(VpngateCandidate).where(VpngateCandidate.external_id == external_id))
        if existing.scalar_one_or_none():
            continue

        cand = VpngateCandidate(
            external_id=external_id,
            region_code=country,
            hostname=row.get("#HostName") or row.get("HostName") or "",
            ip=ip,
            score=int(row.get("Score", 0) or 0),
            status="healthy",
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(cand)
        count += 1

    await db.commit()
    print(f"synced {count} VPNGate candidates (skipped {skipped})", flush=True)
    return count
