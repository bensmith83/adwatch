Anyone who knows anything about me knows I love Bluetooth Low Energy. So naturally, I built a tool for it.

Introducing **adwatch** — an open-source BLE advertisement analyzer that passively scans your environment, classifies every Bluetooth device it finds, and presents everything through a real-time web dashboard.

What started as a weekend curiosity ("what's actually broadcasting around me?") turned into something with 81 protocol parsers — from Apple AirDrop and Find My to Ruuvi sensors, Rivian vehicles, Samsung SmartTags, Sonos speakers, ThermoPro sensors, and dozens more.

The part I'm most proud of is the **Protocol Explorer**. It's a built-in hex viewer and field editor that lets you reverse-engineer unknown BLE payloads, define protocol specs visually, and then auto-generate a parser plugin from your spec. See a device you don't recognize? Capture its advertisements, map out the bytes, click "Generate Plugin," and now adwatch understands it forever.

Under the hood: Python + Bleak for BLE scanning, FastAPI + WebSockets for real-time streaming, SQLite for storage, and a single-page Preact dashboard. No cloud, no accounts, no phoning home — it runs entirely on your local machine with a Bluetooth adapter.

A few things I learned building this:
- BLE is a zoo. Every manufacturer encodes data differently, and many abuse "standard" fields in creative ways (looking at you, ThermoPro, stuffing temperature data into the company ID field)
- A plugin architecture pays for itself fast when you're dealing with 72+ device protocols
- The gap between "I can see hex bytes" and "I understand what this device is saying" is exactly where tooling should live

It's open source and I'd love contributions — especially new parser plugins. If you've ever been curious about the invisible Bluetooth world around you, give it a spin.

github.com/bensmith83/adwatch

#bluetooth #ble #opensource #iot #reverseengineering #python
