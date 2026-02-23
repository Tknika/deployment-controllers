"""Pydantic models for APN configuration endpoints."""

from ipaddress import IPv4Network

from pydantic import BaseModel, Field, field_validator


class ApnModel(BaseModel):
    """APN representation exposed by /core/apns endpoints."""

    name: str = Field(..., min_length=1, description="APN name")
    subnet: str = Field(..., description="IPv4 subnet in CIDR notation")
    interface: str = Field(..., min_length=1, description="UPF interface name")

    @field_validator("name", "interface")
    @classmethod
    def validate_identifier_fields(cls, value: str) -> str:
        """Validate fields that are serialized inside DNN_LIST entries."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be empty")
        if "," in cleaned or ";" in cleaned:
            raise ValueError("value cannot contain ',' or ';'")
        return cleaned

    @field_validator("subnet")
    @classmethod
    def validate_subnet(cls, value: str) -> str:
        """Validate IPv4 subnet in CIDR notation."""
        cleaned = value.strip()
        try:
            IPv4Network(cleaned, strict=False)
        except ValueError as exc:
            raise ValueError("subnet must be a valid IPv4 CIDR subnet") from exc
        return cleaned


class ApnCollectionReplaceRequest(BaseModel):
    """Full APN collection replacement payload."""

    apns: list[ApnModel] = Field(default_factory=list)
