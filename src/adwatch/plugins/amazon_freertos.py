"""AmazonFreeRTOS BLE onboarding / MQTT-proxy plugin.

Per apk-ble-hunting/reports/pentair-pentairhome_passive.md, Pentair Home's
AmazonFreeRTOS stack scans on service UUID
``8a7f1168-48af-4efb-83b5-e679f932ff00``
(`com/amazon/aws/amazonfreertossdk/AmazonFreeRTOSManager.java:70`), which
that report names the **AmazonFreeRTOS DEVICE_INFO service** -- an SDK
UUID, not a Pentair one.

The corpus corroborates that: the very same UUID, plus
``a9d7166a-d72e-40a9-a002-48044cc30100``, also turns up in the unrelated
Bird Buddy bird-feeder bundle (`birdbuddy-app.md:79,83`). Two products with
nothing in common do not independently pick identical custom 128-bit
UUIDs, so both belong to the AmazonFreeRTOS BLE SDK. `pentair-pentairhome_native.md`
guesses the second one is "likely Pentair ScreenLogic"; the Bird Buddy
overlap contradicts that.

So a hit means "an AmazonFreeRTOS-based device is onboarding or bridging to
AWS IoT over BLE" -- it does **not** identify a vendor. Known corpus users:
Pentair AFR salt cells, Bird Buddy feeders. Nothing about device state is
broadcast; telemetry rides the post-connect MQTT proxy characteristics.

Identity is the BLE MAC: no in-payload identifier is advertised.
"""

import hashlib
import re

from adwatch.models import RawAdvertisement, ParseResult
from adwatch.registry import register_parser
from adwatch.plugins.birdbuddy import BIRDBUDDY_NAME_PATTERN

# Bird Buddy feeders run the same SDK; when the advertised name identifies
# one, plugins/birdbuddy.py owns the sighting and this generic plugin stands
# down (mirrors the omron/glucose_meters and oticon/resound arrangements).
_BIRDBUDDY_NAME_RE = re.compile(BIRDBUDDY_NAME_PATTERN)


AFR_DEVICE_INFO_UUID = "8a7f1168-48af-4efb-83b5-e679f932ff00"
AFR_MQTT_PROXY_UUID = "a9d7166a-d72e-40a9-a002-48044cc30100"

_SERVICE_LABELS = [
    (AFR_DEVICE_INFO_UUID, "device_info"),
    (AFR_MQTT_PROXY_UUID, "mqtt_proxy"),
]


@register_parser(
    name="amazon_freertos",
    service_uuid=[AFR_DEVICE_INFO_UUID, AFR_MQTT_PROXY_UUID],
    description="AmazonFreeRTOS BLE onboarding / AWS IoT MQTT proxy (vendor-agnostic)",
    version="1.0.0",
    core=False,
)
class AmazonFreeRTOSParser:
    def parse(self, raw: RawAdvertisement) -> ParseResult | None:
        seen = {u.lower() for u in (raw.service_uuids or [])}
        seen.update(k.lower() for k in (raw.service_data or {}))

        labels = [label for uuid, label in _SERVICE_LABELS if uuid in seen]
        if not labels:
            return None
        if raw.local_name and _BIRDBUDDY_NAME_RE.match(raw.local_name):
            return None

        metadata: dict = {
            "sdk": "amazon-freertos",
            "services": ",".join(labels),
            # The UUIDs come from the SDK, so they identify the stack, not
            # the manufacturer. Known corpus users: Pentair AFR salt cells,
            # Bird Buddy feeders.
            "vendor_agnostic": True,
            "transport": "ble_aws_iot",
        }
        if raw.local_name:
            metadata["device_name"] = raw.local_name

        id_hash = hashlib.sha256(
            f"amazon_freertos:{raw.mac_address}".encode()
        ).hexdigest()[:16]

        return ParseResult(
            parser_name="amazon_freertos",
            beacon_type="amazon_freertos",
            device_class="provisioning",
            identifier_hash=id_hash,
            raw_payload_hex=(raw.manufacturer_data or b"").hex(),
            metadata=metadata,
        )

    def storage_schema(self):
        return None
