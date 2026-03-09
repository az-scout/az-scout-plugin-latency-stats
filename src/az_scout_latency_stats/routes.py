"""API routes for the latency stats plugin."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from az_scout_latency_stats.metadata import (
    AZUREDOCS_DISCLAIMER,
    AZUREDOCS_SOURCE,
    CLOUD63_DISCLAIMER,
    CLOUD63_SOURCE,
    INTER_ZONE_DISCLAIMER,
    INTER_ZONE_METHODOLOGY,
    INTER_ZONE_SOURCE,
)

router = APIRouter()


class LatencyMatrixRequest(BaseModel):
    """Request body for the latency matrix endpoint."""

    regions: list[str]
    mode: Literal["azuredocs", "cloud63"] = "azuredocs"


class InterZoneMatrixRequest(BaseModel):
    """Request body for inter-zone matrix endpoint."""

    region: str


@router.post("/inter-region/matrix")
async def latency_matrix(body: LatencyMatrixRequest) -> dict[str, object]:
    """Return a pairwise RTT latency matrix for the given regions.

    Available at ``/plugins/latency-stats/inter-region/matrix``.
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


@router.get("/inter-region/pairs")
async def latency_pairs() -> dict[str, object]:
    """Return all known latency pairs.

    Available at ``/plugins/latency-stats/inter-region/pairs``.
    """
    from az_scout_latency_stats.latency import list_known_pairs

    return {
        "pairs": list_known_pairs(),
        "source": AZUREDOCS_SOURCE,
    }


@router.get("/inter-region/cloud63-regions")
async def cloud63_regions() -> dict[str, object]:
    """Return the list of regions available in the Cloud63 data.

    Available at ``/plugins/latency-stats/inter-region/cloud63-regions``.
    Triggers a data fetch if the cache is empty or stale.
    """
    from az_scout_latency_stats.cloud63 import (
        get_cloud63_regions,
        refresh_cloud63_data,
    )

    await refresh_cloud63_data()
    return {"regions": get_cloud63_regions()}


@router.get("/inter-zone/regions")
async def inter_zone_regions() -> dict[str, object]:
    """Return the list of regions available for inter-zone latency data."""
    from az_scout_latency_stats.inter_zone import (
        get_inter_zone_regions,
        refresh_inter_zone_data,
    )

    await refresh_inter_zone_data()
    return {"regions": get_inter_zone_regions()}


@router.post("/inter-zone/matrix")
async def inter_zone_matrix(body: InterZoneMatrixRequest) -> dict[str, object]:
    """Return inter-zone AZ latency matrix (P50 RTT) for a selected region."""
    from az_scout_latency_stats.inter_zone import (
        get_inter_zone_matrix,
        refresh_inter_zone_data,
    )

    await refresh_inter_zone_data()
    return {
        **get_inter_zone_matrix(body.region),
        "source": INTER_ZONE_SOURCE,
        "disclaimer": INTER_ZONE_DISCLAIMER,
        "methodology": f"{INTER_ZONE_METHODOLOGY} is used when multiple samples exist.",
    }
