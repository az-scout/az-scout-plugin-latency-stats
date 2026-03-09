"""API routes for the latency stats plugin."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from az_scout_latency_stats.metadata import (
    AZUREDOCS_DISCLAIMER,
    AZUREDOCS_SOURCE,
    CLOUD63_DISCLAIMER,
    CLOUD63_SOURCE,
    INTRA_ZONE_DISCLAIMER,
    INTRA_ZONE_METHODOLOGY,
    INTRA_ZONE_SOURCE,
)

router = APIRouter()


class LatencyMatrixRequest(BaseModel):
    """Request body for the latency matrix endpoint."""

    regions: list[str]
    mode: Literal["azuredocs", "cloud63"] = "azuredocs"


class IntraZoneMatrixRequest(BaseModel):
    """Request body for intra-zone matrix endpoint."""

    region: str


@router.post("/matrix")
async def latency_matrix(body: LatencyMatrixRequest) -> dict[str, object]:
    """Return a pairwise RTT latency matrix for the given regions.

    Available at ``/plugins/latency-stats/matrix``.
    Accepts a JSON body with ``{"regions": [...], "mode": "azuredocs"|"cloud63"}``.
    """
    if body.mode == "cloud63":
        from az_scout_latency_stats.cloud63 import (
            get_cloud63_latency_matrix,
            refresh_cloud63_data,
        )

        await refresh_cloud63_data()
        result = get_cloud63_latency_matrix(body.regions)
        return {
            **result,
            "mode": "cloud63",
            "source": CLOUD63_SOURCE,
            "disclaimer": CLOUD63_DISCLAIMER,
        }

    from az_scout_latency_stats.latency import get_latency_matrix

    result = get_latency_matrix(body.regions)
    return {
        **result,
        "mode": "azuredocs",
        "source": AZUREDOCS_SOURCE,
        "disclaimer": AZUREDOCS_DISCLAIMER,
    }


@router.get("/pairs")
async def latency_pairs() -> dict[str, object]:
    """Return all known latency pairs.

    Available at ``/plugins/latency-stats/pairs``.
    """
    from az_scout_latency_stats.latency import list_known_pairs

    return {
        "pairs": list_known_pairs(),
        "source": AZUREDOCS_SOURCE,
    }


@router.get("/cloud63-regions")
async def cloud63_regions() -> dict[str, object]:
    """Return the list of regions available in the Cloud63 data.

    Available at ``/plugins/latency-stats/cloud63-regions``.
    Triggers a data fetch if the cache is empty or stale.
    """
    from az_scout_latency_stats.cloud63 import (
        get_cloud63_regions,
        refresh_cloud63_data,
    )

    await refresh_cloud63_data()
    return {"regions": get_cloud63_regions()}


@router.get("/intra-zone/regions")
async def intra_zone_regions() -> dict[str, object]:
    """Return the list of regions available for intra-zone latency data."""
    from az_scout_latency_stats.intra_zone import (
        get_intra_zone_regions,
        refresh_intra_zone_data,
    )

    await refresh_intra_zone_data()
    return {"regions": get_intra_zone_regions()}


@router.post("/intra-zone/matrix")
async def intra_zone_matrix(body: IntraZoneMatrixRequest) -> dict[str, object]:
    """Return intra-region AZ latency matrix (P50) for a selected region."""
    from az_scout_latency_stats.intra_zone import (
        get_intra_zone_matrix,
        refresh_intra_zone_data,
    )

    await refresh_intra_zone_data()
    return {
        **get_intra_zone_matrix(body.region),
        "source": INTRA_ZONE_SOURCE,
        "disclaimer": INTRA_ZONE_DISCLAIMER,
        "methodology": f"{INTRA_ZONE_METHODOLOGY} is used when multiple samples exist.",
    }
