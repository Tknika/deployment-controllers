"""
Pydantic models for subscriber management.
"""

from typing import Annotated, Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field, model_validator

PyObjectId = Annotated[str, BeforeValidator(str)]
ImsiStr = Annotated[str, Field(pattern=r"^[0-9]{14,15}$")]


def clean_hex_spaces(v: str) -> str:
    """Remove spaces from hexadecimal string (for WebUI compatibility)."""
    if isinstance(v, str):
        v = v.replace(" ", "")
    return v


Hex32Str = Annotated[str, BeforeValidator(clean_hex_spaces), Field(pattern=r"^[0-9a-fA-F]{32}$")]
Hex4Str = Annotated[str, BeforeValidator(clean_hex_spaces), Field(pattern=r"^[0-9a-fA-F]{4}$")]


class AmbrValueModel(BaseModel):
    """AMBR value with unit."""

    value: int
    unit: int  # 0:bps, 1:Kbps, 2:Mbps, 3:Gbps, 4:Tbps


class AmbrModel(BaseModel):
    """Aggregated Maximum Bit Rate configuration (bidirectional)."""

    downlink: AmbrValueModel = Field(
        default_factory=lambda: AmbrValueModel(value=1000000000, unit=0)
    )
    uplink: AmbrValueModel = Field(
        default_factory=lambda: AmbrValueModel(value=1000000000, unit=0)
    )


class ArpModel(BaseModel):
    """Allocation and Retention Priority."""

    priority_level: int = 8
    pre_emption_capability: int = 1
    pre_emption_vulnerability: int = 2


class QosModel(BaseModel):
    """Quality of Service profile (5QI/QCI)."""

    index: int = 9
    arp: Optional[ArpModel] = Field(default_factory=ArpModel)


class UeModel(BaseModel):
    """UE configuration for static IP assignment."""

    ipv4: Optional[str] = None
    ipv6: Optional[str] = None


class SessionModel(BaseModel):
    """Subscriber session configuration inside a slice (APN)."""

    name: str = "internet"
    type: int = 3  # PDN Type: 1=IPv4, 2=IPv6, 3=IPv4v6
    qos: QosModel = Field(default_factory=QosModel)
    ambr: AmbrModel = Field(default_factory=AmbrModel)
    ue: Optional[UeModel] = None
    pcc_rule: List[Dict[str, Any]] = Field(default_factory=list)
    lbo_roaming_allowed: Optional[bool] = None
    id: Optional[PyObjectId] = Field(
        default_factory=lambda: str(ObjectId()), alias="_id"
    )

    model_config = {
        "populate_by_name": True,
    }


class SliceModel(BaseModel):
    """Network slice configuration."""

    sst: int = 1
    sd: Optional[str] = "000001"
    default_indicator: bool = True
    session: List[SessionModel]
    id: Optional[PyObjectId] = Field(
        default_factory=lambda: str(ObjectId()), alias="_id"
    )

    model_config = {
        "populate_by_name": True,
    }


class SecurityModel(BaseModel):
    """Subscriber security credentials."""

    k: Hex32Str
    amf: Hex4Str = "8000"
    op: Optional[Hex32Str] = None
    opc: Optional[Hex32Str] = None

    @model_validator(mode="after")
    def check_op_or_opc(self) -> "SecurityModel":
        """Ensure only one of OP or OPC is provided."""
        if self.op and self.opc:
            raise ValueError("Provide either OP or OPC, not both.")
        if not self.op and not self.opc:
            raise ValueError("Provide at least one: OP or OPC.")
        return self


class SubscriberSchema(BaseModel):
    """Subscriber document stored in MongoDB."""

    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    schema_version: int = 1
    imsi: ImsiStr
    name: Optional[str] = Field(None, max_length=100)
    msisdn: List[str] = Field(default_factory=list)
    imeisv: List[str] = Field(default_factory=list)
    mme_host: List[str] = Field(default_factory=list)
    mm_realm: List[str] = Field(default_factory=list)
    purge_flag: List[bool] = Field(default_factory=list)
    slice: List[SliceModel]
    security: SecurityModel
    ambr: AmbrModel = Field(default_factory=AmbrModel)
    access_restriction_data: int = 32
    network_access_mode: int = 0
    subscriber_status: int = 0
    operator_determined_barring: int = 0
    subscribed_rau_tau_timer: int = 12
    v: int = Field(default=0, alias="__v")

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }
