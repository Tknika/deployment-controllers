# /core endpoint structure

### Inportant information
[Open5GS JSON API](https://open5gs.org/open5gs/docs/tutorial/07-infoAPI-UE-gNB-session-data/)

- SMF -	/pdu-info: All currently connected UEs + their PDU sessions (IMSI/SUPI, DNN, IPs, S-NSSAI, QoS, state, etc.)
- AMF - /gnb-info: All currently connected gNBs and their supported TAs, PLMNs, SCTP info, number of UEs
- AMF - /ue-info: All currently connected NR UEs and their info, active gNB, tai, security, slices, am_policy
- MME- /enb-info: All currently connected eNBs and their supported TAs, PLMNs, SCTP info, number of UEs
- MME - /ue-info: All currently connected LTE UEs and their info, active eNB, tai, pdn info
> They are exposed on the same HTTP port used by Prometheus metrics (default :9090).

### Endpoints

#### GET /core
Returns information about the available core endpoints

#### GET /core/enb-info
All connected eNBs and their respective TAs, PLMNs, SCTP info, and number of UEs

> Calls should be forwarded to port 9090 of the container named MME

#### GET /core/ue-info
All connected LTE UEs and their info, active eNB, tai, and PDN info

> Calls should be forwarded to port 9090 of the container named MME

#### GET /core/pdu-info
All connected UEs and their PDU sessions (IMSI/SUPI, DNN, IPs, S-NSSAI, QoS, state, etc.)

> Calls should be forwarded to port 9090 of the container named SMF

#### GET /core/info-stream
SSE stream that provides real-time information for `enb-info`, `ue-info` and `pdu-info`.

- Response content type: `text/event-stream`
- Event types: `snapshot`, `update`
- Polling interval is global and shared across all subscribers (default: 2 second)

Behavior:

- On connection, a `snapshot` event is always sent with full data for all 3 resources.
- During the stream lifetime, an `update` event is sent only when there is a real change in one or more resources.
- If Open5GS fails in a polling cycle, no event is emitted in that cycle.
- If Open5GS is unreachable when opening the stream, the endpoint returns an error.

SSE event examples:

```text
event: snapshot
data: {"enb-info":[...],"ue-info":[...],"pdu-info":[...]}

event: update
data: {"ue-info":[...],"pdu-info":[...]}
```

#### GET /core/apns
Returns all APNs defined in `DNN_LIST`.

Response format:

```json
[
	{
		"name": "internet",
		"subnet": "192.168.100.0/24",
		"interface": "ogstun"
	},
	{
		"name": "ims",
		"subnet": "192.168.101.0/24",
		"interface": "ogstun2"
	}
]
```

#### POST /core/apns
Creates a new APN.

Payload:

```json
{
	"name": "m2m",
	"subnet": "192.168.110.0/24",
	"interface": "ogstun3"
}
```

#### PUT /core/apns/{name}
Replaces a single APN by name with a full payload.

Payload:

```json
{
	"name": "internet",
	"subnet": "192.168.100.0/24",
	"interface": "ogstun"
}
```

#### DELETE /core/apns/{name}
Deletes a single APN by name.

#### PUT /core/apns
Replaces the full APN collection in a single operation.

Payload:

```json
{
	"apns": [
		{
			"name": "internet",
			"subnet": "192.168.100.0/24",
			"interface": "ogstun"
		},
		{
			"name": "ims",
			"subnet": "192.168.101.0/24",
			"interface": "ogstun2"
		}
	]
}
```

Notes:

- Source of truth: `DNN_LIST`
- Every mutation triggers environment update with service restart through `/envs`