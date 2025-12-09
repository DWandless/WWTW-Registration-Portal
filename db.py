# db.py
import httpx
from supabase import create_client, ClientOptions
import streamlit as st

def get_supabase():
    url = st.secrets["supabase"]["SUPABASE_URL"]
    key = st.secrets["supabase"]["SUPABASE_KEY"]

    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set in secrets.toml")

    # Disable SSL verification TEMPORARILY - TODO: Change this to be verify=True
    # TODO: Add RLS policies in Supabase dashboard
    insecure_client = httpx.Client(verify=True)

    options = ClientOptions(
        auto_refresh_token=True,
        persist_session=False,
        httpx_client=insecure_client,  # Patch here
    )

    return create_client(url, key, options)

# Create reusable singleton client
supabase = get_supabase()