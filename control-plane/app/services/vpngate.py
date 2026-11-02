"""VPNGate public feed sync.

Feed format (text/plain CSV):
  *vpn_servers
  #HostName,IP,Score,Ping,Speed,CountryLong,CountryShort,...
  public-vpn-1,1.2.3.4,...,Japan,JP,...
  *
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Region, VpngateCandidate

logger = logging.getLogger(__name__)

VPNGATE_CSV_URL = "https://www.vpngate.net/api/iphone/"


def _csv_body(text: str) -> str:
    """Drop the *vpn_servers banner and the leading # on the header row."""
    lines = text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip("\ufeff").lstrip()
        if "HostName" in stripped and "CountryShort" in stripped:
            if stripped.startswith("#"):
                lines[i] = stripped[1:]
            start = i
            break
    body = "\n".join(lines[start:])
    # trailing '*' marker is not a data row
    return body


async def sync_candidates(db: AsyncSession) -> int:
    print("VPNGate sync started", flush=True)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(VPNGATE_CSV_URL)
            resp.raise_for_status()
            text = resp.text
        print(f"VPNGate feed fetched, length={len(text)}", flush=True)
    except Exception as exc:
        print(f"VPNGate fetch failed: {exc}", flush=True)
        return 0

    body = _csv_body(text)
    reader = csv.DictReader(io.StringIO(body))
    print(f"VPNGate columns: {reader.fieldnames}", flush=True)

    count = 0
    skipped = 0
    for row in reader:
        if not row:
            continue
        hostname = (row.get("HostName") or "").strip()
        if not hostname or hostname == "*":
            skipped += 1
            continue
        ip = (row.get("IP") or "").strip()
        country = (row.get("CountryShort") or "").strip().upper()
        if not ip or len(country) != 2:
            skipped += 1
            continue

        region = await db.get(Region, country)
        if not region:
            name = (row.get("CountryLong") or country).strip() or country
            db.add(Region(code=country, name=name))
            await db.flush()

        existing = await db.execute(
            select(VpngateCandidate).where(VpngateCandidate.external_id == hostname)
        )
        cand = existing.scalar_one_or_none()
        score = int(row.get("Score") or 0)
        if cand:
            cand.ip = ip
            cand.region_code = country
            cand.score = score
            cand.status = "healthy"
            cand.last_synced_at = datetime.now(timezone.utc)
            continue

        db.add(
            VpngateCandidate(
                external_id=hostname,
                region_code=country,
                hostname=hostname,
                ip=ip,
                score=score,
                status="healthy",
                last_synced_at=datetime.now(timezone.utc),
            )
        )
        count += 1

    await db.commit()
    print(f"synced {count} new VPNGate candidates (skipped {skipped})", flush=True)
    return count
