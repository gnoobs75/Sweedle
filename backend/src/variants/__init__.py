"""Variants module for asset variants and version history."""

from .router import router
from .schemas import (
    VariantGroupCreate,
    VariantGroupResponse,
    VariantGroupDetail,
    GenerateVariantsRequest,
    GenerateVariantsResponse,
    AssetVersionResponse,
    VersionHistoryResponse,
    CreateVersionRequest,
    SetPrimaryVariantRequest,
)

__all__ = [
    "router",
    "VariantGroupCreate",
    "VariantGroupResponse",
    "VariantGroupDetail",
    "GenerateVariantsRequest",
    "GenerateVariantsResponse",
    "AssetVersionResponse",
    "VersionHistoryResponse",
    "CreateVersionRequest",
    "SetPrimaryVariantRequest",
]
