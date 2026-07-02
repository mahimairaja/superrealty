# Inbound phone calls (SIP)

Give a realtor a real phone number that rings their always-on assistant. A caller dials the
number, Telnyx forwards the call over SIP to LiveKit, LiveKit puts the caller in a room and
dispatches the `realty` agent, and the agent answers exactly as it does for web calls.

The agent already handles SIP callers (`agent/src/utils/room.py: identify()` classifies them and
reads the caller's number from `sip.phoneNumber`). The only new piece is routing + telling the
agent which realtor (tenant) the call is for.

## How the tenant is resolved

Web calls encode the tenant in the room name (`t_{org_id}_{random}`). A SIP room is named by the
provider, so it can't carry that. Instead the **dispatch rule passes the tenant as agent job
metadata** (`roomConfig.agents[].metadata = {"tenant_id": "org_..."}`), and the agent falls back
to it (`tenant_from_metadata` in `agent/src/agent.py`). So each realtor's number maps to their
tenant via its own dispatch rule.

## One-time setup (per deployment)

These steps use accounts you own; they can't be provisioned from this repo.

1. **Telnyx**: buy a number, create a SIP Connection (FQDN/credentials), and point its inbound
   calls at your LiveKit SIP URI (Project Settings → SIP URI, without the `sip:` prefix). Set the
   Destination Number Format to `+E.164` so the number matches the trunk's `+` prefix.
2. **LiveKit inbound trunk** — edit `inbound-trunk.json` (put your real number(s) in `numbers`),
   then:

   ```
   lk sip inbound create infra/sip/inbound-trunk.json
   ```

   Note the returned trunk id (`ST_...`).

## Per realtor (per number)

For each realtor, copy `dispatch-rule.json` and replace:

- `trunk_ids` → the inbound trunk id from above (or omit the field to match all inbound trunks),
- both `org_REPLACE_ME` → that realtor's Clerk **organization id** (their `tenant_id`; it's shown
  in the console URL and in their call link `…/call/<org_id>`).

Then:

```
lk sip dispatch create infra/sip/dispatch-rule.json
```

Now a call to that number rings that realtor's assistant, scoped to their listings and memory.

## Test

Call the number. The agent should answer with the realtor's greeting; the call then behaves like
any web call (qualify the buyer, recommend listings, book a showing, post-call lead SMS).

> The room-name codec (`t_{tenant}_{random}`) and the metadata fallback must stay in sync with
> the backend (`tenant_from_room_name`) and the agent (`parse_tenant_id` / `tenant_from_metadata`).
