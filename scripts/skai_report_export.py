#!/usr/bin/env python3

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests

TOKEN_URL = "https://services.kenshoo.com/api/v1/token"
REPORTS_URL = "https://services.kenshoo.com/api/v1/reports"
DEFAULT_TIMEOUT = 120
DEFAULT_REPORT_PAGE_LIMIT = 2000
VIDEO_HINTS = ("video", "mp4", "mov", "webm", "youtube", "vimeo")
EXCLUDED_BRAND_TEXT_FIELDS = ("CampaignName", "brand", "Headline", "source")
EXCLUDED_BRAND_PATTERNS = (
    re.compile(r"(^|[^A-Z0-9])EXCLUDED_BRAND([^A-Z0-9]|$)"),
    re.compile(r"EXCLUDED BRAND"),
)


def default_field_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "default-field-config.json"


def fallback_skai_env_path() -> Path:
    codex_home = Path(os.getenv("CODEX_HOME") or (Path.home() / ".codex"))
    return codex_home / "skills" / "skai" / ".env"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta un reporte analitico desde Skai para responder preguntas "
            "de performance, comparativas y diagnostico."
        ),
    )
    parser.add_argument("--start-date", required=True, help="Fecha inicio YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="Fecha fin YYYY-MM-DD")
    parser.add_argument("--output-dir", required=True, help="Directorio donde guardar resultados")
    parser.add_argument(
        "--country",
        help="Pais a consultar. Si no se especifica, usa SKAI_COUNTRY o USA",
    )
    parser.add_argument(
        "--field-config",
        help="Ruta a un JSON con group_by y fields. Si se omite, usa el config por defecto del skill",
    )
    parser.add_argument(
        "--profile-ids",
        help="Lista separada por comas de profile_id a incluir, por ejemplo 775,776",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "json", "both"),
        default="both",
        help="Formato de salida",
    )
    parser.add_argument(
        "--env-file",
        help="Ruta a un .env especifico. Si se omite, intenta varios paths conocidos",
    )
    parser.add_argument(
        "--input-json",
        help="Ruta a un JSON ya descargado de Skai para probar sin llamar al API",
    )
    parser.add_argument("--client-id", help="Sobrescribe SKAI_CLIENT_ID")
    parser.add_argument("--refresh-token", help="Sobrescribe SKAI_REFRESH_TOKEN")
    parser.add_argument("--ks", help="Sobrescribe SKAI_KS")
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Timeout en segundos para llamadas HTTP",
    )
    parser.add_argument(
        "--save-raw-response",
        help="Guarda la respuesta original del API antes de procesarla",
    )
    parser.add_argument(
        "--exclude-brand",
        action="store_true",
        help="Excluye EXCLUDED_BRAND y Excluded Brand",
    )
    parser.add_argument(
        "--exclude-video",
        action="store_true",
        help="Excluye creatividades de video",
    )
    return parser.parse_args()


def load_env_file(env_file: str | None) -> str | None:
    candidate_paths: list[Path] = []
    if env_file:
        candidate_paths.append(Path(env_file).expanduser())
    else:
        candidate_paths.append(Path(__file__).resolve().parents[1] / ".env")
        candidate_paths.append(fallback_skai_env_path())
        candidate_paths.append(Path.cwd() / ".env")

    for path in candidate_paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))
        return str(path.resolve())
    return None


def load_field_config(path: str | None) -> dict[str, Any]:
    config_path = Path(path).expanduser().resolve() if path else default_field_config_path()
    with open(config_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if "fields" not in payload or not isinstance(payload["fields"], list):
        raise ValueError("El field config debe incluir una lista 'fields'.")
    if "group_by" not in payload or not isinstance(payload["group_by"], list):
        raise ValueError("El field config debe incluir una lista 'group_by'.")

    return {
        "group_by": payload["group_by"],
        "fields": payload["fields"],
        "_source_path": str(config_path),
    }


def get_required_value(cli_value: str | None, env_name: str) -> str:
    if cli_value:
        return cli_value
    env_value = os.getenv(env_name)
    if env_value:
        return env_value
    raise ValueError(f"Falta {env_name}. Define la variable de entorno o pasala por CLI.")


def get_optional_value(cli_value: str | None, env_name: str) -> str | None:
    if cli_value:
        return cli_value
    return os.getenv(env_name)


def country_env_suffix(country: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", (country or "").strip().upper()).strip("_")
    return normalized


def get_country_aware_value(
    cli_value: str | None,
    env_name: str,
    country: str,
    *,
    required: bool = False,
) -> str | None:
    if cli_value:
        return cli_value

    suffix = country_env_suffix(country)
    if suffix:
        country_env_name = f"{env_name}_{suffix}"
        if country_env_name in os.environ:
            value = os.environ.get(country_env_name)
            if required and not value:
                raise ValueError(
                    f"Falta {country_env_name}. Define la variable de entorno o pasala por CLI."
                )
            return value

    if required:
        return get_required_value(None, env_name)
    return get_optional_value(None, env_name)


def get_access_token(client_id: str, refresh_token: str, timeout: int) -> str:
    response = requests.post(
        TOKEN_URL,
        data={"refresh_token": refresh_token, "client_id": client_id},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_report(
    access_token: str,
    ks: str,
    start_date: str,
    end_date: str,
    field_config: dict[str, Any],
    timeout: int,
) -> tuple[dict[str, Any], list[dict[str, str | None]]]:
    requested_fields = [
        {"name": field["name"], "group": field["group"]}
        for field in field_config["fields"]
    ]
    base_payload = {
        "entity": "AD",
        "group_by": field_config["group_by"],
        "date_range": {"start_date": start_date, "end_date": end_date},
        "limit": DEFAULT_REPORT_PAGE_LIMIT,
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    removed_fields: list[dict[str, str | None]] = []
    merged_payload: dict[str, Any] | None = None
    total_records = 0
    page = 0

    while True:
        payload = dict(base_payload)
        payload["fields"] = requested_fields
        payload["page"] = page
        response = requests.post(
            f"{REPORTS_URL}?ks={ks}",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError:
            invalid_field = parse_invalid_field_error(response)
            if invalid_field and remove_requested_field(requested_fields, invalid_field):
                removed_fields.append(
                    {"name": invalid_field[0], "group": invalid_field[1]}
                )
                continue
            raise

        page_payload = response.json()
        entities = page_payload.get("entities", [])

        if merged_payload is None:
            merged_payload = page_payload
        else:
            merged_entities = merged_payload.setdefault("entities", [])
            for index, entity in enumerate(entities):
                if index >= len(merged_entities):
                    merged_entities.append(entity)
                    continue
                merged_entities[index].setdefault("records", [])
                merged_entities[index]["records"].extend(entity.get("records", []))

        page_record_count = 0
        for index, entity in enumerate(entities):
            page_record_count += len(entity.get("records", []))
            if index < len((merged_payload or {}).get("entities", [])):
                merged_payload["entities"][index]["total"] = entity.get("total")

        total_records += page_record_count
        expected_total = (
            max((entity.get("total") or 0) for entity in (merged_payload or {}).get("entities", []))
            if merged_payload
            else 0
        )
        if page_record_count == 0 or (expected_total and total_records >= expected_total):
            break
        page += 1

    return merged_payload or {"entities": []}, removed_fields


def parse_invalid_field_error(response: requests.Response) -> tuple[str, str | None] | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    message = str(payload.get("error_message") or "")
    match = re.search(r"Column name (.+?) doesn't exist in group ([A-Za-z0-9_ ()-]+)", message)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def remove_requested_field(
    requested_fields: list[dict[str, Any]],
    invalid_field: tuple[str, str | None],
) -> bool:
    invalid_name, invalid_group = invalid_field
    for index, field in enumerate(requested_fields):
        same_name = str(field.get("name") or "").strip() == invalid_name
        same_group = invalid_group is None or str(field.get("group") or "").strip() == invalid_group
        if same_name and same_group:
            requested_fields.pop(index)
            return True
    return False


def load_input_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def extract_scalar(value: Any) -> Any:
    if isinstance(value, list):
        if not value:
            return None
        extracted = [extract_scalar(item) for item in value]
        extracted = [item for item in extracted if item not in (None, "")]
        if not extracted:
            return None
        if len(extracted) == 1:
            return extracted[0]
        return " | ".join(str(item) for item in extracted)

    if isinstance(value, dict):
        if "value" in value:
            return extract_scalar(value["value"])
        if "display_value" in value:
            return extract_scalar(value["display_value"])

    return value


def coerce_value(value: Any, field_type: str | None) -> Any:
    if value in (None, ""):
        return None

    if field_type in (None, "string"):
        return str(value).strip()

    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip()
        cleaned = re.sub(r"[$%\u00a3\u20ac]", "", text.replace(",", ""))
        try:
            number = float(cleaned)
        except ValueError:
            return text

    if field_type == "integer":
        return int(number) if number.is_integer() else number
    if field_type == "number":
        return int(number) if number.is_integer() else number
    return value


def normalize_records(report_payload: dict[str, Any], field_config: dict[str, Any]) -> list[dict[str, Any]]:
    entities = report_payload.get("entities", [])
    records: list[dict[str, Any]] = []

    for entity in entities:
        for record in entity.get("records", []):
            raw_values = record.get("record_values", {})
            normalized: dict[str, Any] = {}
            for field in field_config["fields"]:
                value = None
                for key in [field["name"], *field.get("aliases", [])]:
                    if key in raw_values:
                        value = extract_scalar(raw_values[key])
                        break
                normalized[field["output"]] = coerce_value(value, field.get("type"))
            records.append(normalized)

    return records


def parse_profile_ids(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def normalize_country_value(value: Any) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "USA": "US",
        "UNITED STATES": "US",
        "UNITED STATES OF AMERICA": "US",
        "ESPANA": "ES",
        "SPAIN": "ES",
    }
    return aliases.get(text, text)


def filter_records(
    records: list[dict[str, Any]],
    country: str,
    profile_ids: list[str],
    exclude_brand: bool,
    exclude_video: bool,
) -> tuple[list[dict[str, Any]], bool, bool, int, int]:
    normalized_country = normalize_country_value(country)
    country_present = any(record.get("Country") not in (None, "") for record in records)
    allowed_profile_ids = set(profile_ids)
    profile_filter_applied = bool(allowed_profile_ids)
    filtered: list[dict[str, Any]] = []
    excluded_brand_rows = 0
    video_excluded_rows = 0

    for record in records:
        record_profile_id = str(record.get("profile_id") or "").strip()
        # Business rule: profile filters override country heuristics because the account
        # structure is the stronger scoping signal when country fields are inconsistent.
        if allowed_profile_ids and record_profile_id not in allowed_profile_ids:
            continue

        record_country = normalize_country_value(record.get("Country"))
        if not allowed_profile_ids and country_present and record_country != normalized_country:
            continue

        # Business rule: excluded brand groups and video creatives can distort creative CTR
        # comparisons, so the run summary keeps explicit counts for every row removed.
        if exclude_brand and is_excluded_brand_record(record):
            excluded_brand_rows += 1
            continue

        if exclude_video and is_video_record(record):
            video_excluded_rows += 1
            continue

        filtered.append(record)

    return (
        filtered,
        country_present and not allowed_profile_ids,
        profile_filter_applied,
        excluded_brand_rows,
        video_excluded_rows,
    )


def is_excluded_brand_record(record: dict[str, Any]) -> bool:
    for field_name in EXCLUDED_BRAND_TEXT_FIELDS:
        value = str(record.get(field_name) or "").strip().upper()
        if not value:
            continue
        if any(pattern.search(value) for pattern in EXCLUDED_BRAND_PATTERNS):
            return True
    return False


def is_video_record(record: dict[str, Any]) -> bool:
    ad_type = str(record.get("AdTypeName") or "").strip().lower()
    if any(token in ad_type for token in VIDEO_HINTS):
        return True
    image_url = str(record.get("ImageUrl") or "").strip().lower()
    if any(token in image_url for token in VIDEO_HINTS):
        return True
    return False


def count_unique_non_empty_rows(rows: list[dict[str, Any]], field_name: str) -> int:
    values = {
        str(row.get(field_name) or "").strip()
        for row in rows
        if str(row.get(field_name) or "").strip()
    }
    return len(values)


def output_columns(field_config: dict[str, Any]) -> list[str]:
    return [field["output"] for field in field_config["fields"]]


def write_exports(records: list[dict[str, Any]], destination: Path, file_format: str, columns: list[str]) -> None:
    if file_format in ("csv", "both"):
        write_csv(records, destination.with_suffix(".csv"), columns)
    if file_format in ("json", "both"):
        write_json(records, destination.with_suffix(".json"))


def write_csv(records: list[dict[str, Any]], path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            writer.writerow({column: record.get(column, "") for column in columns})


def write_json(payload: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def save_raw_response(raw_payload: dict[str, Any], path: str) -> None:
    write_json(raw_payload, Path(path))


def build_export_manifest(base_path: Path, file_format: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    if file_format in ("csv", "both"):
        manifest["csv"] = str(base_path.with_suffix(".csv"))
    if file_format in ("json", "both"):
        manifest["json"] = str(base_path.with_suffix(".json"))
    return manifest


def main() -> int:
    args = parse_args()
    loaded_env_path = load_env_file(args.env_file)
    if not args.country:
        args.country = os.getenv("SKAI_COUNTRY") or "USA"

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        field_config = load_field_config(args.field_config)
        profile_ids = parse_profile_ids(
            get_country_aware_value(args.profile_ids, "SKAI_PROFILE_IDS", args.country) or ""
        )

        if args.input_json:
            report_payload = load_input_json(args.input_json)
            removed_fields: list[dict[str, str | None]] = []
        else:
            client_id = get_required_value(args.client_id, "SKAI_CLIENT_ID")
            refresh_token = get_country_aware_value(
                args.refresh_token,
                "SKAI_REFRESH_TOKEN",
                args.country,
                required=True,
            )
            ks = get_country_aware_value(args.ks, "SKAI_KS", args.country, required=True)
            access_token = get_access_token(client_id, refresh_token, args.request_timeout)
            report_payload, removed_fields = fetch_report(
                access_token=access_token,
                ks=ks,
                start_date=args.start_date,
                end_date=args.end_date,
                field_config=field_config,
                timeout=args.request_timeout,
            )

        if args.save_raw_response:
            save_raw_response(report_payload, args.save_raw_response)

        records = normalize_records(report_payload, field_config)
        filtered_records, country_filter_applied, profile_filter_applied, excluded_brand_rows, video_excluded_rows = filter_records(
            records,
            args.country,
            profile_ids,
            args.exclude_brand,
            args.exclude_video,
        )
        columns = output_columns(field_config)

        write_exports(
            filtered_records,
            output_dir / "skai_report_records",
            args.format,
            columns,
        )

        summary = {
            "country": args.country,
            "requested_profile_ids": profile_ids,
            "start_date": args.start_date,
            "end_date": args.end_date,
            "field_config": field_config["_source_path"],
            "group_by": field_config["group_by"],
            "columns": columns,
            "env_file_used": loaded_env_path,
            "raw_input_json": str(Path(args.input_json).expanduser().resolve()) if args.input_json else None,
            "records_received": len(records),
            "records_after_filters": len(filtered_records),
            "country_filter_applied": country_filter_applied,
            "profile_filter_applied": profile_filter_applied,
            "excluded_brand_filter_applied": args.exclude_brand,
            "excluded_brand_rows": excluded_brand_rows,
            "video_exclusion_applied": args.exclude_video,
            "video_rows_excluded": video_excluded_rows,
            "unique_ad_ids": count_unique_non_empty_rows(filtered_records, "AdId"),
            "unique_campaign_ids": count_unique_non_empty_rows(filtered_records, "CampaignId"),
            "unique_brands": count_unique_non_empty_rows(filtered_records, "brand"),
            "unique_sources": count_unique_non_empty_rows(filtered_records, "source"),
            "dropped_requested_fields": removed_fields,
            "output_dir": str(output_dir),
            "files": {
                "skai_report_records": build_export_manifest(output_dir / "skai_report_records", args.format),
            },
        }
        write_json(summary, output_dir / "summary.json")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except requests.HTTPError as exc:
        print(f"HTTP error: {exc}", file=sys.stderr)
        if exc.response is not None:
            print(exc.response.text, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
