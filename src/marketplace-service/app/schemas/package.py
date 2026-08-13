"""生态市场 Pydantic schemas（入参校验 + 出参契约）。"""
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class PackageCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=160)
    name: str = Field(..., min_length=1, max_length=160)
    package_type: str  # skill | connector | expert
    publisher: str = Field(..., min_length=1, max_length=160)
    summary: Optional[str] = Field(None, max_length=280)
    description: Optional[str] = None
    license: Optional[str] = Field(None, max_length=60)
    price_model: str = "free"  # free | paid | subscription
    price_cents: int = 0
    currency: str = "CNY"
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    homepage: Optional[str] = Field(None, max_length=512)
    repository: Optional[str] = Field(None, max_length=512)
    icon_url: Optional[str] = Field(None, max_length=512)
    supported_platforms: list[str] = Field(default_factory=list)
    is_public: bool = True
    tenant_id: Optional[UUID] = None

    @field_validator("package_type")
    @classmethod
    def _type(cls, v):
        if v not in ("skill", "connector", "expert"):
            raise ValueError("package_type must be one of skill/connector/expert")
        return v

    @field_validator("price_model")
    @classmethod
    def _price_model(cls, v):
        if v not in ("free", "paid", "subscription"):
            raise ValueError("price_model must be one of free/paid/subscription")
        return v

    @field_validator("price_cents")
    @classmethod
    def _price_cents(cls, v):
        if v < 0:
            raise ValueError("price_cents must be >= 0")
        return v


class PackageOut(BaseModel):
    id: UUID
    slug: str
    name: str
    package_type: str
    publisher: str
    summary: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    price_model: str
    price_cents: int
    currency: str
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    homepage: Optional[str] = None
    repository: Optional[str] = None
    icon_url: Optional[str] = None
    supported_platforms: list[str] = Field(default_factory=list)
    version: str
    install_count: int
    rating_avg: float
    rating_count: int
    is_public: bool
    tenant_id: Optional[UUID] = None
    owner_id: Optional[UUID] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PackageVersionCreate(BaseModel):
    version: str = Field(..., max_length=32)
    manifest: Optional[dict] = None
    changelog: Optional[str] = None
    download_url: Optional[str] = Field(None, max_length=512)
    artifact_hash: Optional[str] = Field(None, max_length=128)
    min_platform_version: Optional[str] = Field(None, max_length=32)


class PackageVersionOut(BaseModel):
    id: UUID
    package_id: UUID
    version: str
    manifest: Optional[dict] = None
    changelog: Optional[str] = None
    download_url: Optional[str] = None
    artifact_hash: Optional[str] = None
    min_platform_version: Optional[str] = None
    created_at: Optional[str] = None


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=160)
    body: Optional[str] = None
    reviewer_id: Optional[UUID] = None


class ReviewOut(BaseModel):
    id: UUID
    package_id: UUID
    tenant_id: Optional[UUID] = None
    reviewer_id: Optional[UUID] = None
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    created_at: Optional[str] = None


class MarketplaceStats(BaseModel):
    total_packages: int
    by_type: dict[str, int]
    total_installs: int
    total_reviews: int
    top_packages: list[dict] = Field(default_factory=list)


class BrowseResponse(BaseModel):
    items: list[PackageOut]
    total: int
    page: int
    size: int
