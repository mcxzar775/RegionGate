"""VPNGate public feed sync.

The embedded OpenVPN profile is stored in raw_meta for the control plane
only. Candidate API responses do not include it.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Region, VpngateCandidate

VPNGATE_CSV_URL = "https://www.vpngate.net/api/iphone/"
PARSER = "v3"


def _csv_body(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip("\ufeff").strip()
        if "HostName" in stripped and "IP" in stripped and "CountryShort" in stripped:
            lines[i] = stripped[1:] if stripped.startswith("#") else stripped
            start = i
            break
    return "\n".join(lines[start:])


async def sync_candidates(db: AsyncSession) -> int:
    print(f"VPNGate sync started parser={PARSER}", flush=True)
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(VPNGATE_CSV_URL)
            resp.raise_for_status()
            text = resp.text
        print(f"VPNGate feed fetched, length={len(text)}", flush=True)
    except Exception as exc:
        print(f"VPNGate fetch failed: {exc}", flush=True)
        return 0

    reader = csv.DictReader(io.StringIO(_csv_body(text)))
    print(f"VPNGate columns: {reader.fieldnames}", flush=True)

    count = 0
    updated = 0
    skipped = 0
    for row in reader:
        if not row:
            continue
        hostname = (row.get("HostName") or "").strip()
        if not hostname or hostname.startswith("*") or hostname.startswith("#"):
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

        try:
            score = int(float(row.get("Score") or 0))
        except ValueError:
            score = 0
        ovpn_b64 = (row.get("OpenVPN_ConfigData_Base64") or "").strip()
        meta = {"operator": (row.get("Operator") or "")[:120], "has_ovpn": bool(ovpn_b64)}
        if ovpn_b64:
            meta["ovpn_b64"] = ovpn_b64

        existing = await db.execute(
            select(VpngateCandidate).where(VpngateCandidate.external_id == hostname)
        )
        cand = existing.scalar_one_or_none()
        if cand:
            cand.ip = ip
            cand.region_code = country
            cand.hostname = hostname
            cand.score = score
            cand.status = "healthy"
            cand.raw_meta = meta
            cand.last_synced_at = datetime.now(timezone.utc)
            updated += 1
            continue

        db.add(
            VpngateCandidate(
                external_id=hostname,
                region_code=country,
                hostname=hostname,
                ip=ip,
                score=score,
                status="healthy",
                raw_meta=meta,
                last_synced_at=datetime.now(timezone.utc),
            )
        )
        count += 1

    await db.commit()
    print(
        f"synced {count} new, updated {updated}, skipped {skipped} parser={PARSER}",
        flush=True,
    )
    return count + updated
