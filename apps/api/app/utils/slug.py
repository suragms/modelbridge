from __future__ import annotations

import re
import uuid


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60] or "org"


async def unique_slug(db, name: str, exclude_id: uuid.UUID | None = None) -> str:
    from sqlalchemy import select

    from app.models.organization import Organization

    base = slugify(name)
    slug = base
    n = 1
    while True:
        q = select(Organization.id).where(Organization.slug == slug)
        if exclude_id:
            q = q.where(Organization.id != exclude_id)
        result = await db.execute(q)
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base}-{n}"
        n += 1
