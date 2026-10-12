"""Launch AJ's Academy with its session-authorized media route."""
import os

import streamlit as st

import secure_media


academy = st.App(
    "app.py",
    routes=secure_media.routes(),
)

if __name__ == "__main__":
    academy.run(
        config={
            "server.address": "0.0.0.0",
            "server.port": int(os.environ.get("PORT", "5000")),
            "server.headless": True,
            "browser.gatherUsageStats": False,
        }
    )
