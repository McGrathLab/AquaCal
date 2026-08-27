"""Zenodo deposition uploader: create an UNPUBLISHED draft and stream one file into it.

This is an operational utility, not part of the `aquacal` public API. It exists so the
real-rig calibration archive can be deposited on Zenodo as two records -- immutable
inputs and a versioned results package -- over the REST API rather than through a
browser tab that has to survive an hours-long multi-gigabyte transfer.

It cannot publish. There is no publish code path and no discard code path in this file.
Minting a DOI is one-way and permanent, so it stays a deliberate human act performed in
the Zenodo web UI (phase 29 decision D-29-01). The access token this tool expects is
minted with the `deposit:write` scope only and deliberately without the publish-actions
scope, so the omission is enforced by the credential as well as by the code. The tool
also never asks Zenodo to reserve a DOI on a draft (D-29-03); no identifier exists until
the author presses Publish.

The access token is read from the process environment only -- never from a command-line
argument (arguments are visible in `ps` output and in shell history) and never from a
file. Export the sandbox token as ZENODO_SANDBOX_TOKEN and the production token as
ZENODO_TOKEN. Every Authorization header is scrubbed before it can reach a log line or a
re-raised error message.

Choosing the host is always an explicit act: exactly one of --sandbox or --base-url is
required and neither carries a default, so a rehearsal cannot silently reach production.

Not intended to be imported. Run it directly:

    python scripts/zenodo_upload.py --sandbox \\
        --metadata scripts/zenodo_metadata_a.json \\
        --file /tmp/record-a.zip --name real-rig-inputs.zip \\
        --out .planning/phases/29-gate-verification-results-commit/rehearsal.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = "https://sandbox.zenodo.org/api"

_SANDBOX_TOKEN_VAR = "ZENODO_SANDBOX_TOKEN"
_PRODUCTION_TOKEN_VAR = "ZENODO_TOKEN"

_REDACTED = "Bearer <redacted>"

# A connect timeout is cheap and uniform; the read timeout is what has to stretch for a
# multi-gigabyte PUT, so it is a flag. Neither is ever None -- an unbounded read timeout
# lets a hung socket block forever, and Zenodo 504s on long uploads are documented.
_CONNECT_TIMEOUT = 30
_JSON_READ_TIMEOUT = 120

# Zenodo rejects an open dataset deposition that is missing any of these. Checking them
# here means a malformed metadata block fails in the first second rather than after a
# four-hour transfer.
_REQUIRED_METADATA_FIELDS = (
    "upload_type",
    "title",
    "description",
    "creators",
    "access_right",
    "license",
    "publication_date",
)

# Values this tool refuses to deviate from. Both records in phase 29 are open datasets;
# anything else is a metadata mistake, not a configuration choice.
_REQUIRED_METADATA_VALUES = {"upload_type": "dataset", "access_right": "open"}

_MAX_SERVER_DETAIL_CHARS = 2000


def scrub_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of `headers` with any authorization value redacted.

    Args:
        headers: Request headers, possibly carrying a bearer credential.

    Returns:
        A new dict with every `Authorization` value replaced by a fixed marker.
    """
    scrubbed = dict(headers)
    for key in scrubbed:
        if key.lower() == "authorization":
            scrubbed[key] = _REDACTED
    return scrubbed


def _scrub_text(text: str, token: str) -> str:
    """Return `text` with any occurrence of the access token redacted.

    `requests` exception messages can quote a request URL or header, so nothing derived
    from an exception is logged or re-raised without passing through here first.

    Args:
        text: Arbitrary text about to be logged or re-raised.
        token: The access token to redact.

    Returns:
        The text with the token replaced by a fixed marker.
    """
    if not token:
        return text
    return text.replace(token, "<redacted>")


def _server_detail(exc: requests.RequestException, token: str) -> str:
    """Return the server's response body for an HTTP error, scrubbed and truncated.

    Zenodo reports metadata validation failures in the response body, which is the only
    place that says *which* field was rejected.

    Args:
        exc: The raised `requests` exception.
        token: The access token to redact from the body.

    Returns:
        A ` -- server said: ...` suffix, or an empty string when there is no body.
    """
    response = getattr(exc, "response", None)
    if response is None:
        return ""
    body = (response.text or "").strip()
    if not body:
        return ""
    return f" -- server said: {_scrub_text(body, token)[:_MAX_SERVER_DETAIL_CHARS]}"


def resolve_token(sandbox: bool) -> str:
    """Read the Zenodo access token for the selected host from the environment.

    The token is never accepted as a command-line argument: arguments are visible in
    `ps` output and land in shell history. Sandbox and production are separate Zenodo
    registrations with separate tokens, so they get separate variables -- that is also
    what stops a sandbox-intended run from authenticating against production.

    Args:
        sandbox: True when `--sandbox` was given.

    Returns:
        The access token.

    Raises:
        ValueError: If the required environment variable is unset or empty.
    """
    variable = _SANDBOX_TOKEN_VAR if sandbox else _PRODUCTION_TOKEN_VAR
    token = os.environ.get(variable, "")
    if not token:
        raise ValueError(
            f"Environment variable '{variable}' is unset or empty. "
            "Export it in this shell; do not pass a token on the command line."
        )
    return token


def load_metadata(path: Path) -> dict:
    """Load and validate a Zenodo deposition metadata block from a JSON file.

    The file *is* the metadata block: its keys are Zenodo's, so the author can read and
    correct exactly what will be deposited without reading any Python.

    Args:
        path: Path to the metadata JSON file.

    Returns:
        The parsed metadata dict.

    Raises:
        ValueError: If the file is not a JSON object, is missing a required field, or
            sets a field this tool refuses to deviate from.
        OSError: If the file cannot be read.
    """
    with open(path, encoding="utf-8") as fp:
        metadata = json.load(fp)

    if not isinstance(metadata, dict):
        raise ValueError(
            f"Metadata file '{path}' must contain a JSON object, "
            f"got {type(metadata).__name__}."
        )

    for field in _REQUIRED_METADATA_FIELDS:
        if not metadata.get(field):
            raise ValueError(
                f"Metadata file '{path}' is missing required field '{field}'. "
                "Zenodo rejects an open dataset deposition without it."
            )

    for field, expected in _REQUIRED_METADATA_VALUES.items():
        if metadata[field] != expected:
            raise ValueError(
                f"Metadata file '{path}' sets '{field}' to {metadata[field]!r}; "
                f"this tool deposits only {expected!r} records."
            )

    return metadata


def md5_of(path: Path, block: int = 1 << 20) -> str:
    """Compute the MD5 digest of a file.

    Args:
        path: File to digest.
        block: Read size in bytes. The default is widened from the download path's 8 KiB
            because this side of the round trip digests multi-gigabyte archives.

    Returns:
        The lowercase hex digest, without an algorithm prefix.
    """
    hash_obj = hashlib.md5()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(block), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def create_draft(base_url: str, token: str, metadata: dict) -> dict:
    """Create a new UNPUBLISHED deposition carrying `metadata`.

    No DOI is requested or reserved: under D-29-03 no identifier exists until the author
    publishes the draft by hand.

    Args:
        base_url: API base, e.g. `https://sandbox.zenodo.org/api`.
        token: Access token.
        metadata: A validated Zenodo metadata block.

    Returns:
        The parsed deposition, carrying `id` and `links` (including links.bucket, the
        only URL a file upload targets).

    Raises:
        RuntimeError: If the request fails or the response is not a JSON object.
    """
    url = f"{base_url}/deposit/depositions"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    logger.info("Creating draft at %s", url)
    logger.debug("POST %s headers=%s", url, scrub_headers(headers))
    try:
        response = requests.post(
            url,
            json={"metadata": metadata},
            headers=headers,
            timeout=(_CONNECT_TIMEOUT, _JSON_READ_TIMEOUT),
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"failed to create draft at {url}: {_scrub_text(str(exc), token)}"
            f"{_server_detail(exc, token)}"
        ) from exc

    if not isinstance(body, dict):
        raise RuntimeError(f"create-draft response from {url} was not a JSON object")
    return body


def update_metadata(
    base_url: str, token: str, deposition_id: int, metadata: dict
) -> dict:
    """Replace the metadata block of an existing draft.

    Used to correct a draft in place and to add the A<->B cross-link, which cannot exist
    at creation time because the other record does not exist yet.

    Args:
        base_url: API base.
        token: Access token.
        deposition_id: The draft's numeric id.
        metadata: The full replacement metadata block.

    Returns:
        The parsed deposition.

    Raises:
        RuntimeError: If the request fails or the response is not a JSON object.
    """
    url = f"{base_url}/deposit/depositions/{deposition_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    logger.info("Updating metadata on draft %s at %s", deposition_id, url)
    logger.debug("PUT %s headers=%s", url, scrub_headers(headers))
    try:
        response = requests.put(
            url,
            json={"metadata": metadata},
            headers=headers,
            timeout=(_CONNECT_TIMEOUT, _JSON_READ_TIMEOUT),
        )
        response.raise_for_status()
        body = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"failed to update draft {deposition_id}: {_scrub_text(str(exc), token)}"
            f"{_server_detail(exc, token)}"
        ) from exc

    if not isinstance(body, dict):
        raise RuntimeError(f"update-metadata response from {url} was not a JSON object")
    return body


def put_file(
    bucket_url: str,
    token: str,
    path: Path,
    name: str,
    max_retries: int = 5,
    read_timeout: int = 3600,
    expected_md5: str | None = None,
) -> dict:
    """Stream one file into a deposition's bucket and verify the round trip by MD5.

    The whole transfer sits inside the `try`, so the file handle is reopened on every
    attempt: retrying with an already-consumed file object uploads zero bytes, which is
    the single most important structural property here. The file object is passed to
    `requests` directly rather than a generator, so a real `Content-Length` is sent
    instead of chunked transfer encoding.

    A checksum mismatch is raised as a `RuntimeError` inside the loop and is therefore
    itself retryable -- silent truncation is a transport failure, not a fatal one.

    Args:
        bucket_url: The draft's `links.bucket` URL.
        token: Access token.
        path: Local file to upload.
        name: Key the file takes inside the record.
        max_retries: Attempts before giving up.
        read_timeout: Socket read timeout in seconds. Never None.
        expected_md5: Precomputed local hex digest. Computed here when omitted; passing
            it avoids a second full read of a multi-gigabyte archive.

    Returns:
        The bucket response body, carrying `key`, `size`, `checksum` and `version_id`.
        That body is the round-trip proof.

    Raises:
        RuntimeError: If every attempt fails.
        OSError: If the local file cannot be read.
    """
    expected = expected_md5 or md5_of(path)
    total = path.stat().st_size
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{bucket_url}/{name}"
    logger.info("Uploading %s -> %s (%d bytes, md5:%s)", path, url, total, expected)
    logger.debug("PUT %s headers=%s", url, scrub_headers(headers))

    for attempt in range(max_retries):
        try:
            with open(path, "rb") as fp:
                with tqdm.wrapattr(
                    fp,
                    "read",
                    total=total,
                    desc=name,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as wrapped:
                    response = requests.put(
                        url,
                        data=wrapped,
                        headers=headers,
                        timeout=(_CONNECT_TIMEOUT, read_timeout),
                    )
            response.raise_for_status()
            body = response.json()

            # Guard the response shape before trusting it: a missing or non-string
            # checksum is a failed attempt, not a KeyError traceback.
            if not isinstance(body, dict):
                raise RuntimeError(
                    f"bucket response for {name!r} was not a JSON object"
                )
            returned = body.get("checksum")
            if not isinstance(returned, str):
                raise RuntimeError(
                    f"bucket response for {name!r} carries no usable 'checksum' "
                    f"field; keys were {sorted(body)}"
                )
            if returned != f"md5:{expected}":
                raise RuntimeError(
                    f"round-trip checksum mismatch for {name!r}: server returned "
                    f"{returned}, local digest is md5:{expected}"
                )
            return body

        except (requests.RequestException, RuntimeError) as exc:
            detail = _scrub_text(str(exc), token) + _scrub_text(
                _server_detail(exc, token)
                if isinstance(exc, requests.RequestException)
                else "",
                token,
            )
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"upload failed after {max_retries} attempts: {detail}"
                ) from exc
            wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s, 8s
            logger.warning(
                "Upload failed (attempt %d/%d): %s", attempt + 1, max_retries, detail
            )
            logger.warning("Retrying in %ds...", wait_time)
            time.sleep(wait_time)

    raise RuntimeError(f"upload failed after {max_retries} attempts")


def _append_record(out_path: Path, record: dict) -> None:
    """Append one result record to the evidence transcript.

    Args:
        out_path: Transcript file; created if absent, never truncated.
        record: The JSON-serialisable result to append.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as fp:
        fp.write("\n" + "-" * 80 + "\n")
        fp.write(json.dumps(record, indent=2, sort_keys=True))
        fp.write("\n")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured `argparse.ArgumentParser` for this script.
    """
    parser = argparse.ArgumentParser(description=__doc__)

    # Required, mutually exclusive, and NEITHER has a default. Selecting the host is
    # always an explicit act, so "uploaded to production while intending sandbox"
    # cannot happen by omission.
    host = parser.add_mutually_exclusive_group(required=True)
    host.add_argument(
        "--sandbox",
        action="store_true",
        help=(
            f"Target {SANDBOX_BASE_URL} and read the token from "
            f"{_SANDBOX_TOKEN_VAR}. Sandbox DOIs use the 10.5072 test prefix."
        ),
    )
    host.add_argument(
        "--base-url",
        type=str,
        help=(
            "Target this API base explicitly, e.g. https://zenodo.org/api. The token "
            f"is then read from {_PRODUCTION_TOKEN_VAR}."
        ),
    )

    parser.add_argument(
        "--metadata",
        type=Path,
        required=True,
        help="JSON file holding the Zenodo deposition metadata block.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Local file to upload. Omit (with --name) for a metadata-only draft.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Key the uploaded file takes inside the record. Required with --file.",
    )
    parser.add_argument(
        "--deposition-id",
        type=int,
        default=None,
        help="Update this existing draft instead of creating a new one.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Evidence transcript to append the result JSON to.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Upload attempts before giving up (default: 5).",
    )
    parser.add_argument(
        "--read-timeout",
        type=int,
        default=3600,
        help="Socket read timeout in seconds for the upload (default: 3600).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python scripts/zenodo_upload.py`.

    Args:
        argv: Argument list (defaults to `sys.argv[1:]` via `argparse`).

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if (args.file is None) != (args.name is None):
        logger.error(
            "ERROR: --file and --name go together; give both, or neither for a "
            "metadata-only draft."
        )
        return 1

    base_url = SANDBOX_BASE_URL if args.sandbox else args.base_url.rstrip("/")

    try:
        token = resolve_token(args.sandbox)
        metadata = load_metadata(args.metadata)
    except (OSError, ValueError) as exc:
        logger.error("ERROR: %s", exc)
        return 1

    record: dict = {
        "utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_url": base_url,
        "sandbox": bool(args.sandbox),
        "metadata_file": str(args.metadata),
        "metadata_title": metadata.get("title"),
    }

    try:
        if args.deposition_id is not None:
            record["action"] = "update_metadata"
            deposition = update_metadata(base_url, token, args.deposition_id, metadata)
        else:
            record["action"] = "create_draft"
            deposition = create_draft(base_url, token, metadata)
    except RuntimeError as exc:
        logger.error("ERROR: %s", exc)
        return 1

    links = deposition.get("links") or {}
    # The bucket URL comes straight from the draft's links.bucket and is the only URL a
    # file PUT targets; the legacy form-based files endpoint caps at 100 MB and cannot
    # carry this project's 4.35 GB archive.
    bucket_url = links.get("bucket")
    record["deposition_id"] = deposition.get("id")
    record["links_html"] = links.get("html")
    record["bucket_url_present"] = bool(bucket_url)
    record["submitted"] = deposition.get("submitted")
    record["state"] = deposition.get("state")
    record["deposition_response"] = deposition

    logger.info("Deposition id: %s", record["deposition_id"])
    logger.info("Draft URL:     %s", record["links_html"])

    if args.file is not None:
        if not bucket_url:
            logger.error(
                "ERROR: deposition %s carries no bucket URL; cannot upload.",
                record["deposition_id"],
            )
            return 1
        try:
            local_md5 = md5_of(args.file)
            upload = put_file(
                bucket_url,
                token,
                args.file,
                args.name,
                args.max_retries,
                args.read_timeout,
                expected_md5=local_md5,
            )
        except (OSError, RuntimeError) as exc:
            logger.error("ERROR: %s", exc)
            return 1
        record["local_file"] = str(args.file)
        record["local_md5"] = f"md5:{local_md5}"
        record["upload_response"] = upload
        record["round_trip_verified"] = upload.get("checksum") == f"md5:{local_md5}"
        logger.info("Server checksum: %s", upload.get("checksum"))
        logger.info("Local  checksum: md5:%s", local_md5)

    _append_record(args.out, record)

    logger.info(
        "TOTAL: %s on deposition %s, UNPUBLISHED; recorded to %s",
        record["action"],
        record["deposition_id"],
        args.out,
    )
    logger.info(
        "This tool does not publish. Press Publish yourself in the Zenodo web UI."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
