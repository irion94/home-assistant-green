#!/usr/bin/env python3
"""
Build normalized CSV and summary from Home Assistant registry JSON files.
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

RAW_DIR = Path("data/inventory/raw/latest")
DERIVED_DIR = Path("data/inventory/derived")


def load_json(filename: str) -> Dict[str, Any]:
    """Load JSON file, return empty dict if missing."""
    filepath = RAW_DIR / filename
    if not filepath.exists():
        print(f"⚠ {filename} not found, skipping")
        return {}

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_value(data: Dict, key: str, default: str = "") -> str:
    """Safely get value from dict, return default if missing."""
    value = data.get(key, default)
    return str(value) if value is not None else default


def build_devices_csv(device_registry: Dict, area_registry: Dict) -> List[Dict]:
    """Build devices CSV data."""
    areas = {a["id"]: a["name"] for a in area_registry.get("data", {}).get("areas", [])}
    devices = device_registry.get("data", {}).get("devices", [])

    rows = []
    for device in devices:
        rows.append({
            "id": get_value(device, "id"),
            "name": get_value(device, "name_by_user") or get_value(device, "name"),
            "manufacturer": get_value(device, "manufacturer"),
            "model": get_value(device, "model"),
            "sw_version": get_value(device, "sw_version"),
            "area": areas.get(device.get("area_id", ""), ""),
            "via_device": get_value(device, "via_device_id"),
            "disabled_by": get_value(device, "disabled_by"),
        })

    return rows


def build_entities_csv(entity_registry: Dict, area_registry: Dict) -> List[Dict]:
    """Build entities CSV data."""
    areas = {a["id"]: a["name"] for a in area_registry.get("data", {}).get("areas", [])}
    entities = entity_registry.get("data", {}).get("entities", [])

    rows = []
    for entity in entities:
        entity_id = get_value(entity, "entity_id")
        domain = entity_id.split(".")[0] if "." in entity_id else ""

        rows.append({
            "entity_id": entity_id,
            "name": get_value(entity, "name") or get_value(entity, "original_name"),
            "device_id": get_value(entity, "device_id"),
            "platform": get_value(entity, "platform"),
            "domain": domain,
            "area": areas.get(entity.get("area_id", ""), ""),
            "enabled": "yes" if not entity.get("disabled_by") else "no",
            "disabled_by": get_value(entity, "disabled_by"),
            "unit": get_value(entity, "unit_of_measurement"),
        })

    return rows


def build_integrations_csv(config_entries: Dict) -> List[Dict]:
    """Build integrations CSV data."""
    entries = config_entries.get("data", {}).get("entries", [])

    rows = []
    for entry in entries:
        rows.append({
            "domain": get_value(entry, "domain"),
            "title": get_value(entry, "title"),
            "source": get_value(entry, "source"),
            "state": get_value(entry, "state"),
            "entry_id": get_value(entry, "entry_id"),
        })

    return rows


def build_areas_csv(area_registry: Dict) -> List[Dict]:
    """Build areas CSV data."""
    areas = area_registry.get("data", {}).get("areas", [])

    rows = []
    for area in areas:
        rows.append({
            "area_id": get_value(area, "id"),
            "name": get_value(area, "name"),
        })

    return rows


def write_csv(filename: str, rows: List[Dict], fieldnames: List[str]):
    """Write CSV file."""
    if not rows:
        print(f"⚠ No data for {filename}, skipping")
        return

    filepath = DERIVED_DIR / filename
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ {filename} ({len(rows)} rows)")


def build_summary(devices: List[Dict], entities: List[Dict], integrations: List[Dict], areas: List[Dict]) -> str:
    """Build summary markdown."""
    summary = []
    summary.append(f"# Home Assistant Inventory Summary\n")
    summary.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    summary.append(f"**Source:** `data/inventory/raw/latest/`\n\n")

    # Totals
    summary.append(f"## Totals\n")
    summary.append(f"- **Devices:** {len(devices)}\n")
    summary.append(f"- **Entities:** {len(entities)}\n")
    summary.append(f"- **Integrations:** {len(integrations)}\n")
    summary.append(f"- **Areas:** {len(areas)}\n\n")

    # Devices by manufacturer
    manufacturers = {}
    for device in devices:
        mfr = device["manufacturer"] or "Unknown"
        manufacturers[mfr] = manufacturers.get(mfr, 0) + 1

    if manufacturers:
        summary.append(f"## Devices by Manufacturer\n")
        for mfr, count in sorted(manufacturers.items(), key=lambda x: -x[1]):
            summary.append(f"- {mfr}: {count}\n")
        summary.append("\n")

    # Entities by domain
    domains = {}
    for entity in entities:
        domain = entity["domain"] or "unknown"
        domains[domain] = domains.get(domain, 0) + 1

    if domains:
        summary.append(f"## Entities by Domain\n")
        for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
            summary.append(f"- {domain}: {count}\n")
        summary.append("\n")

    # Integrations by state
    states = {}
    for integration in integrations:
        state = integration["state"] or "unknown"
        states[state] = states.get(state, 0) + 1

    if states:
        summary.append(f"## Integrations by State\n")
        for state, count in sorted(states.items(), key=lambda x: -x[1]):
            summary.append(f"- {state}: {count}\n")
        summary.append("\n")

    # Top integrations
    integration_counts = {}
    for integration in integrations:
        domain = integration["domain"] or "unknown"
        integration_counts[domain] = integration_counts.get(domain, 0) + 1

    if integration_counts:
        summary.append(f"## Integrations by Domain\n")
        for domain, count in sorted(integration_counts.items(), key=lambda x: -x[1]):
            summary.append(f"- {domain}: {count}\n")
        summary.append("\n")

    return "".join(summary)


def main():
    """Main execution."""
    print("[build_inventory] Loading registry files...")

    # Load JSON files
    device_registry = load_json("core.device_registry")
    entity_registry = load_json("core.entity_registry")
    area_registry = load_json("core.area_registry")
    config_entries = load_json("core.config_entries")

    # Create output directory
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)

    print("[build_inventory] Building CSV files...")

    # Build CSV data
    devices = build_devices_csv(device_registry, area_registry)
    entities = build_entities_csv(entity_registry, area_registry)
    integrations = build_integrations_csv(config_entries)
    areas = build_areas_csv(area_registry)

    # Write CSV files
    write_csv("devices.csv", devices, [
        "id", "name", "manufacturer", "model", "sw_version", "area", "via_device", "disabled_by"
    ])
    write_csv("entities.csv", entities, [
        "entity_id", "name", "device_id", "platform", "domain", "area", "enabled", "disabled_by", "unit"
    ])
    write_csv("integrations.csv", integrations, [
        "domain", "title", "source", "state", "entry_id"
    ])
    write_csv("areas.csv", areas, [
        "area_id", "name"
    ])

    # Build summary
    print("[build_inventory] Building summary...")
    summary = build_summary(devices, entities, integrations, areas)
    summary_path = DERIVED_DIR / "summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"✓ summary.md")

    print(f"[build_inventory] ✓ Done. Outputs in: {DERIVED_DIR}")


if __name__ == "__main__":
    main()
