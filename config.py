"""
Unified configuration & GCP authentication bootstrap.

Priority: Streamlit Secrets > Environment Variables > Defaults
"""

import os
import tempfile

import streamlit as st


# ---------------------------------------------------------------------------
# get_setting: single entry-point for all config values
# ---------------------------------------------------------------------------

def get_setting(key, default=None):
    """Return a config value with priority: st.secrets > os.getenv > default."""
    try:
        val = st.secrets[key]
        if val is not None:
            return str(val).strip()
    except Exception:
        pass
    return os.getenv(key, default)


# ---------------------------------------------------------------------------
# GCP service-account bootstrap (for Streamlit Cloud)
# ---------------------------------------------------------------------------

def bootstrap_gcp_auth():
    """
    If ``GCP_SA_JSON`` is present in Streamlit Secrets, write it to a temp
    file and set ``GOOGLE_APPLICATION_CREDENTIALS`` so that all Google Cloud
    client libraries authenticate automatically.

    * Does nothing when ``GOOGLE_APPLICATION_CREDENTIALS`` is already set.
    * Does nothing when ``GCP_SA_JSON`` is missing (local .env workflow).
    """
    # Already configured – respect existing setting
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        print("[AUTH] GOOGLE_APPLICATION_CREDENTIALS already set, skipping bootstrap")
        return

    sa_json = get_setting("GCP_SA_JSON")
    if not sa_json:
        print("[AUTH] GCP_SA_JSON not found in secrets/env, skipping bootstrap")
        return

    try:
        print("[AUTH] using sa_json from secrets")

        # Write to a temp file that persists for the lifetime of the process
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", prefix="gcp_sa_", delete=False
        )
        tmp.write(sa_json)
        tmp.flush()
        tmp.close()

        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
        print(f"[AUTH] wrote temp credentials: {tmp.name}")
    except Exception as exc:
        msg = f"[AUTH][ERROR] Failed to bootstrap GCP credentials: {exc}"
        print(msg)
        st.error(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_vertex_mode():
    """Return True when both project ID and credentials are available."""
    return bool(
        get_setting("GCP_PROJECT_ID")
        and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )


def auth_label():
    """Return a short human-readable label describing current auth mode."""
    if is_vertex_mode():
        src = "secrets" if get_setting("GCP_SA_JSON") else "env"
        return f"Vertex SA ({src})"
    if get_setting("GOOGLE_API_KEY"):
        return "API Key"
    return "None"
