"""Parent-controlled, validated Academy state and media backups."""
from __future__ import annotations

import copy
import hashlib
import io
import json
import re
import uuid
import zipfile
from datetime import datetime, timezone

import store as db

FORMAT = "ajs-academy-backup"
VERSION = 1
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_UNPACKED_BYTES = 600 * 1024 * 1024
MAX_MEDIA_FILES = 5000
MAX_MEDIA_FILE_BYTES = 40 * 1024 * 1024
MEDIA_MARKER = "__academy_backup_media__"
MEDIA_PATH = re.compile(r"media/[a-f0-9]{32}\.bin\Z")
SECRET_KEYS = {
    "password", "parentpassword", "secret", "clientsecret", "credential",
    "credentials", "token", "accesstoken", "refreshtoken", "session",
    "sessionid", "cookie", "authorization", "apikey", "privatekey",
    "databaseurl", "connectionstring", "serviceaccount", "privateobjectdir",
}


def state_digest(state):
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe_state_value(value, media, download):
    if isinstance(value, dict):
        if isinstance(value.get("bucket"), str) and isinstance(value.get("path"), str):
            asset_path = f"media/{uuid.uuid4().hex}.bin"
            content = download(value)
            if not isinstance(content, bytes):
                content = bytes(content)
            if len(content) > MAX_MEDIA_FILE_BYTES:
                raise ValueError("A saved attachment is larger than the supported 40 MB limit.")
            media[asset_path] = content
            mime = value.get("mime")
            name = value.get("name")
            return {
                MEDIA_MARKER: asset_path,
                "mime": mime if isinstance(mime, str) else "application/octet-stream",
                "name": name if isinstance(name, str) else "family-attachment",
            }
        cleaned = {}
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in SECRET_KEYS or any(
                part in normalized for part in (
                    "password", "secret", "credential", "token", "cookie",
                    "authorization", "apikey", "privatekey",
                )
            ):
                continue
            cleaned[key] = _safe_state_value(item, media, download)
        return cleaned
    if isinstance(value, list):
        return [_safe_state_value(item, media, download) for item in value]
    return value


def build_archive(state, download=db.download):
    """Create a ZIP with JSONB records and the bytes for every stored attachment."""
    media = {}
    portable_state = _safe_state_value(copy.deepcopy(state), media, download)
    if len(media) > MAX_MEDIA_FILES:
        raise ValueError("This family backup contains too many attachments.")
    manifest = {
        "format": FORMAT,
        "version": VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "state": portable_state,
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("manifest.json", json.dumps(
            manifest, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8"))
        for path, content in media.items():
            archive.writestr(path, content)
    result = output.getvalue()
    if len(result) > MAX_ARCHIVE_BYTES:
        raise ValueError("The backup is larger than the supported 200 MB download limit.")
    return result


def _normalize_state(state):
    if not isinstance(state, dict) or not isinstance(state.get("settings"), dict):
        raise ValueError("The backup does not contain valid Academy family records.")
    for key, default in db.DEFAULT.items():
        if key not in state:
            state[key] = copy.deepcopy(default)
        if not isinstance(state[key], type(default)):
            raise ValueError("The backup has an invalid Academy record section.")
    for key, default in db.DEFAULT["settings"].items():
        if key not in state["settings"]:
            state["settings"][key] = copy.deepcopy(default)
        if not isinstance(state["settings"][key], type(default)):
            raise ValueError("The backup has invalid parent settings.")
    try:
        json.dumps(state, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("The backup contains unsupported record values.") from exc
    return state


def _find_media_references(value, references):
    if isinstance(value, dict):
        if MEDIA_MARKER in value:
            if set(value) != {MEDIA_MARKER, "mime", "name"}:
                raise ValueError("The backup has an invalid attachment reference.")
            path = value[MEDIA_MARKER]
            if not isinstance(path, str) or not MEDIA_PATH.fullmatch(path):
                raise ValueError("The backup has an invalid attachment path.")
            if path in references:
                raise ValueError("The backup reuses an attachment path.")
            if not isinstance(value["mime"], str) or not isinstance(value["name"], str):
                raise ValueError("The backup has invalid attachment details.")
            references.add(path)
            return
        if "bucket" in value or "path" in value:
            raise ValueError("The backup contains a storage path instead of an included attachment.")
        for item in value.values():
            _find_media_references(item, references)
    elif isinstance(value, list):
        for item in value:
            _find_media_references(item, references)


def inspect_archive(payload):
    """Validate the complete archive and return a preview ready for explicit restore."""
    if not isinstance(payload, bytes) or not payload or len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("Choose a non-empty Academy backup smaller than 200 MB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError("This file is not a valid Academy backup ZIP.") from exc

    with archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(entries) > MAX_MEDIA_FILES + 1 or len(names) != len(set(names)):
            raise ValueError("The backup contains too many files or duplicate paths.")
        if "manifest.json" not in names:
            raise ValueError("The backup is missing its family-record manifest.")
        if any(item.is_dir() or item.flag_bits & 1 for item in entries):
            raise ValueError("The backup contains an unsupported ZIP entry.")
        if sum(item.file_size for item in entries) > MAX_UNPACKED_BYTES:
            raise ValueError("The backup expands beyond the supported size limit.")
        if archive.getinfo("manifest.json").file_size > 10 * 1024 * 1024:
            raise ValueError("The backup manifest is larger than the supported limit.")
        if any(item.file_size > MAX_MEDIA_FILE_BYTES for item in entries if item.filename != "manifest.json"):
            raise ValueError("The backup contains an attachment larger than 40 MB.")

        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, zipfile.BadZipFile) as exc:
            raise ValueError("The backup manifest is unreadable.") from exc
        if (
            not isinstance(manifest, dict)
            or manifest.get("format") != FORMAT
            or manifest.get("version") != VERSION
        ):
            raise ValueError("This backup was not created by a supported AJ’s Academy version.")
        state = _normalize_state(manifest.get("state"))
        references = set()
        _find_media_references(state, references)
        expected_names = references | {"manifest.json"}
        if set(names) != expected_names:
            raise ValueError("The backup has missing or unexpected files.")

        media = {}
        try:
            for path in references:
                media[path] = archive.read(path)
        except (KeyError, zipfile.BadZipFile, RuntimeError) as exc:
            raise ValueError("An attachment in the backup is damaged or unreadable.") from exc

    return {
        "state": state,
        "media": media,
        "summary": {
            "sections": {
                key: len(value) if isinstance(value, (list, dict)) else 1
                for key, value in state.items()
            },
            "attachments": len(media),
        },
    }


def _restore_media(value, uploaded):
    if isinstance(value, dict):
        if MEDIA_MARKER in value:
            path = value[MEDIA_MARKER]
            return {**uploaded[path], "mime": value["mime"], "name": value["name"]}
        return {key: _restore_media(item, uploaded) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_media(item, uploaded) for item in value]
    return value


def _delete_uploaded(meta):
    db.storage_client().bucket(meta["bucket"]).blob(meta["path"]).delete()


def restore_archive(
    preview, expected_current_digest, *, upload=db.upload, change=db.change, delete=_delete_uploaded
):
    """Upload included media, then atomically replace state only if its preview is current."""
    uploaded = {}
    try:
        for path, content in preview["media"].items():
            reference = preview["state"]
            # The archive has already been validated; MIME/name are carried by its marker.
            marker = path
            metadata = _find_media_metadata(reference, marker)
            uploaded[path] = upload(content, metadata["mime"], metadata["name"])
        restored_state = _restore_media(copy.deepcopy(preview["state"]), uploaded)

        def replace(current):
            if state_digest(current) != expected_current_digest:
                raise ValueError(
                    "Family records changed after the preview. Review the current data and preview again."
                )
            current.clear()
            current.update(restored_state)

        change(replace)
        return True
    except Exception:
        if delete:
            for metadata in uploaded.values():
                try:
                    delete(metadata)
                except Exception:
                    pass
        raise


def _find_media_metadata(value, path):
    if isinstance(value, dict):
        if value.get(MEDIA_MARKER) == path:
            return {"mime": value["mime"], "name": value["name"]}
        for item in value.values():
            found = _find_media_metadata(item, path)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_media_metadata(item, path)
            if found:
                return found
    return None
