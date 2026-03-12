"""Advertisement processing pipeline."""

from __future__ import annotations

from adwatch.models import RawAdvertisement


class Pipeline:
    def __init__(self, raw_storage, classifier, registry, websocket_emitter=None, db=None):
        self._raw_storage = raw_storage
        self._classifier = classifier
        self._registry = registry
        self._ws = websocket_emitter
        self._db = db

    async def process(self, raw: RawAdvertisement) -> None:
        classification = self._classifier.classify(raw)
        parsers = self._registry.match(raw)
        parser_names = []

        stable_key = None
        for parser in parsers:
            result = parser.parse(raw)
            if result is not None:
                parser_names.append(result.parser_name)
                if result.stable_key and stable_key is None:
                    stable_key = result.stable_key
                if result.storage_table and result.storage_row and self._db:
                    cols = ", ".join(result.storage_row.keys())
                    placeholders = ", ".join("?" for _ in result.storage_row)
                    await self._db.execute(
                        f"INSERT INTO {result.storage_table} ({cols}) VALUES ({placeholders})",
                        list(result.storage_row.values()),
                    )
                if result.event_type and self._ws:
                    await self._ws.emit(result.event_type, {
                        "result": result,
                        "raw": raw,
                    })

        await self._raw_storage.save(raw, classification, parsed_by=parser_names or None, stable_key=stable_key)

        if self._ws:
            await self._ws.emit("sighting", {
                "raw": raw,
                "classification": classification,
            })
