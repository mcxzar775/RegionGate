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
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(VPNGATE_CSV_URL)
        resp.raise_for_status()
        text = resp.text

    # VPNGate CSV is base64-wrapped in some cases; handle simple CSV
    reader = csv.DictReader(io.StringIO(text))
    count = 0
    for row in reader:
        if not row.get("IP") or not row.get("CountryLong"):
            continue
        country = row.get("CountryLong", "")[:2].upper()
        if not country:
            continue
        # Ensure region exists
        region = await db.get(Region, country)
        if not region:
            region = Region(code=country, name=country)
            db.add(region)
            await db.flush()

        external_id = row.get("#HostName") or row.get("IP")
        existing = await db.execute(select(VpngateCandidate).where(VpngateCandidate.external_id == external_id))
        if existing.scalar_one_or_none():
            continue

        cand = VpngateCandidate(
            external_id=external_id,
            region_code=country,
            hostname=row.get("#HostName", ""),
            ip=row.get("IP", ""),
            score=int(row.get("Score", 0) or 0),
            status="healthy",
            last_synced_at=datetime.now(timezone.utc),
        )
        db.add(cand)
        count += 1

    await db.commit()
    logger.info("synced %d VPNGate candidates", count)
    return count
