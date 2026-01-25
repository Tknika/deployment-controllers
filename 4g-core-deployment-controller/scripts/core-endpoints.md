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