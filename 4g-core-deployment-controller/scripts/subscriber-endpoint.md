# "/core/subscribers" endpoint structure

### Important information

Open5GS stores subscribers in the **open5gs** database (by default), within the **subscribers** collection.
Exact example of a JSON document for a 5G SA subscriber:

```json
{
  "imsi": "999700000000001",
  "subscribed_rau_tau_timer": 12,
  "network_access_mode": 0,
  "subscriber_status": 0,
  "access_restriction_data": 32,
  "slice": [
    {
      "sst": 1,
      "sd": "000001",
      "default_indicator": true,
      "session": [
        {
          "nssai": {
            "sst": 1,
            "sd": "000001"
          },
          "qos": {
            "index": 9,
            "arp": {
              "priority_level": 8,
              "pre_emption_capability": 1,
              "pre_emption_vulnerability": 1
            }
          },
          "ambr": {
            "uplink": { "value": 1, "unit": 3 },
            "downlink": { "value": 1, "unit": 3 }
          }
        }
      ]
    }
  ],
  "security": {
    "k": "465B5CE8B199B49FAA5F0A2EE238A6BC",
    "amf": "8000",
    "op": null,
    "opc": "E8ED3BEA45975D93131D796449866F5B"
  },
  "ambr": {
    "uplink": { "value": 1, "unit": 3 },
    "downlink": { "value": 1, "unit": 3 }
  },
  "schema_version": 1
}
```

### Key fields

- imsi: Must be a string. It is the logical primary key.
- security:
  - k: SIM key (32-character hexadecimal).
  - op / opc: Only one of the two should be present (the other can be null or an empty string). The WebUI usually uses opc.
  - amf: Usually 8000.
- slice: It is an array. A subscriber can have multiple slices.
  - sst (Slice/Service Type): Integer (e.g., 1 for eMBB).
  - sd (Slice Differentiator): 6-character hexadecimal (e.g., "ffffff" or "000001").
- ambr (Aggregated Maximum Bit Rate):
  - value: The number.
  - unit: The multiplier. (0: bps, 1: Kbps, 2: Mbps, 3: Gbps).
- qos.index: Refers to 5QI (in 5G) or QCI (in 4G). The value 9 is the standard for general internet.

### Subscriber model (Pydantic)

```python
from pydantic import BaseModel, Field, BeforeValidator, field_validator, model_validator
from typing import List, Optional, Annotated

PyObjectId = Annotated[str, BeforeValidator(str)]
ImsiStr = Annotated[str, Field(pattern=r"^[0-9]{14,15}$")]
Hex32Str = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{32}$")]
Hex4Str = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{4}$")]

class AmbrModel(BaseModel):
    value: int
    unit: int # 0:bps, 1:Kbps, 2:Mbps, 3:Gbps

class QosModel(BaseModel):
    index: int = 9
    priority_level: int = 8

class SessionModel(BaseModel):
    nssai: dict = Field(default_factory=lambda: {"sst": 1})
    qos: QosModel = Field(default_factory=QosModel)
    ambr: AmbrModel

class SliceModel(BaseModel):
    sst: int = 1
    sd: Optional[str] = "000001"
    default_indicator: bool = True
    session: List[SessionModel]

class SecurityModel(BaseModel):
    k: Hex32Str
    amf: Hex4Str = "8000"
    op: Optional[Hex32Str] = None
    opc: Optional[Hex32Str] = None

    @model_validator(mode='after')
    def check_op_or_opc(self) -> 'SecurityModel':
        if self.op and self.opc:
            raise ValueError('Debe proporcionarse OP o OPC, pero no ambos.')
        if not self.op and not self.opc:
            raise ValueError('Debe proporcionarse al menos uno: OP o OPC.')
        return self

class SubscriberSchema(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    imsi: ImsiStr
    name: Optional[str] = Field(None, max_length=100)
    subscribed_rau_tau_timer: int = 12
    network_access_mode: int = 0
    subscriber_status: int = 0
    access_restriction_data: int = 32
    slice: List[SliceModel]
    security: SecurityModel
    ambr: AmbrModel
    schema_version: int = 1
```

### Endpoint implementation

```python
from fastapi import APIRouter, HTTPException, status, Query
from typing import List

router = APIRouter(prefix="/core")

# --- 1. GET: List all subscribers ---
@router.get("/subscribers", response_model=List[SubscriberSchema])
async def get_subscribers(
    name: Optional[str] = None,
    sst: Optional[int] = None,
    sd: Optional[str] = None,
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0)
):
    query = {}

    # Filter by name (partial, case-insensitive search)
    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    # Filter by Slice (SST and optionally SD)
    if sst is not None:
        slice_filter = {"sst": sst}
        if sd:
            slice_filter["sd"] = sd
        
        # $elemMatch searches for documents that have at least one element in the 'slice' array that matches
        query["slice"] = {"$elemMatch": slice_filter}

    subscribers = []
    cursor = subscriber_collection.find(query).skip(offset).limit(limit)
    
    async for document in cursor:
        subscribers.append(document)
        
    return subscribers

@router.post("/core/subscriber")
async def register_subscriber(subscriber: SubscriberSchema):
    # 1. Check if the IMSI already exists
    existing = await subscriber_collection.find_one({"imsi": subscriber.imsi})
    if existing:
        raise HTTPException(status_code=400, detail="IMSI is already registered")

    # 2. Convert the Pydantic model to a dictionary (JSON)
    subscriber_dict = subscriber.dict()

    # 3. Insert directly into the Open5GS collection
    try:
        await subscriber_collection.insert_one(subscriber_dict)
        return {"status": "success", "imsi": subscriber.imsi}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. DELETE: Delete a subscriber by IMSI ---
@router.delete("/subscribers/{imsi}")
async def delete_subscriber(imsi: str):
    delete_result = await subscriber_collection.delete_one({"imsi": imsi})
    
    if delete_result.deleted_count == 1:
        return {"status": "success", "message": f"Subscriber {imsi} deleted"}
    
    raise HTTPException(
        status_code=404, 
        detail=f"Subscriber with IMSI {imsi} not found"
    )

# --- 4. PUT: Edit an existing subscriber ---
@router.put("/subscribers/{imsi}")
async def update_subscriber(imsi: str, updated_data: SubscriberSchema):
    # Verify that the IMSI in the body matches the one in the URL 
    # (or simply force the URL one in the object)
    update_dict = updated_data.dict()
    update_dict["imsi"] = imsi 

    # replace_one is safer to ensure the schema remains intact
    result = await subscriber_collection.replace_one(
        {"imsi": imsi}, 
        update_dict
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404, 
            detail=f"No se pudo actualizar: IMSI {imsi} no encontrado"
        )

    return {"status": "success", "message": f"Suscriptor {imsi} actualizado"}
```

### Technical Implementation Details

- Unique Index: Open5GS creates a unique index on the imsi field within MongoDB. If you try to insert a duplicate, Mongo will throw an error that your API must catch.

- AMBR Units: Remember that Open5GS uses an integer system for units:
  3 = Gbps

  2 = Mbps

  1 = Kbps

- OP vs OPC: In most modern SIMs (like those from Sysmocom or similar), opc is used. If you are going to use opc, make sure that the op field in the JSON is strictly null (None in Python). If both have values, the core might exhibit unexpected behaviors depending on the version.

- Core Consistency: Once your API inserts the document, you do not need to restart Open5GS. The MME (4G) or the UDM/UDR (5G) query the database in real-time every time they receive an Attach Request or a Registration Request.

- Name Search: If you search ?name=sensor, the API will return "Sensor_01", "sensor_vibration", etc. Thanks to the $options: "i" flag.

- Slice Search (SST/SD): * If you only pass sst=1, it will bring all subscribers that have the eMBB slice configured (SST 1).

-  If you pass sst=1&sd=000001, it will be much more specific.