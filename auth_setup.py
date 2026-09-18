#!/usr/bin/env python3
"""
One-time OAuth2 setup for machines without a usable browser.

The server's normal flow spins up a local web server and opens a browser at
http://localhost:8080. On a remote VM, a container, or over plain SSH there is
no browser to open and no way to reach that port, so the flow never completes.

This helper splits the flow in two: it prints an authorization URL you open on
whatever machine *does* have a browser, then takes the redirect URL back from
you and exchanges it for a token. The token is written to the same location the
server reads from, so once this finishes the server just works.

Usage:
    python auth_setup.py            # authenticate, refusing to clobber a token
    python auth_setup.py --force    # re-authenticate, replacing any token
    python auth_setup.py --status   # report what credentials are in place

Not needed if you are using a service account - see docs/setup.md.
"""

import argparse
import os
import sys
from pathlib import Path

# The redirect lands on http://localhost, which oauthlib rejects as insecure
# transport by default. It is a loopback address that never leaves the machine
# holding the browser, which is exactly the flow Google documents for desktop
# clients. Both must be set before google_auth_oauthlib is imported.
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
# Google frequently grants scopes in a different order, or adds ones it decides
# are implied. Without this, that mismatch raises instead of succeeding.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv  # noqa: E402
from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from google_mcp_server.auth import GoogleAuthManager, find_service_account_key  # noqa: E402


def build_auth_manager() -> GoogleAuthManager:
    """Construct the manager the server would, so scopes and paths match."""
    load_dotenv()

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080")
    additional = os.getenv("GOOGLE_ADDITIONAL_SCOPES", "")

    return GoogleAuthManager(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        additional_scopes=additional.split() if additional else None,
    )


def show_status(manager: GoogleAuthManager) -> int:
    """Report which credentials are in place, without changing anything."""
    if manager.use_service_account:
        print(f"Service account key: {manager.service_account_file}")
        print("The server authenticates with this key. No OAuth token needed.")
        return 0

    print(f"OAuth client ID: {manager.client_id}")
    print(f"Token file:      {manager.token_file}")
    if not manager.token_file.exists():
        print("\nNo token yet. Run this script without --status to create one.")
        return 1

    print("\nToken present. Verifying...")
    user_info = manager.get_user_info()
    if not user_info:
        print("❌ Token is present but not usable. Re-run with --force.")
        return 1
    print(f"✅ Authenticated as {user_info.get('name')} ({user_info.get('email')})")
    return 0


def run_manual_flow(manager: GoogleAuthManager) -> int:
    """Print an auth URL, take the redirect back, exchange it for a token."""
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": manager.client_id,
                "client_secret": manager.client_secret,
                "redirect_uris": [manager.redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        manager.scopes,
    )
    flow.redirect_uri = manager.redirect_uri

    auth_url, _ = flow.authorization_url(
        access_type="offline",      # we need a refresh token, not just an access token
        prompt="consent",           # force one, even if this account consented before
        include_granted_scopes="true",
    )

    print("\n" + "=" * 72)
    print("STEP 1 - Open this URL in a browser on any machine:\n")
    print(auth_url)
    print("\n" + "=" * 72)
    print(f"""
STEP 2 - Approve the access request.

Your browser will then be redirected to {manager.redirect_uri} and will most
likely show a connection error. That is expected: nothing is listening there.
The part that matters is in the address bar.

STEP 3 - Copy the *entire* URL out of the address bar and paste it below.
It looks like:

    {manager.redirect_uri}/?state=...&code=4/0A...&scope=...
""")
    print("=" * 72)

    try:
        response = input("\nPaste the full redirect URL (or just the code): ").strip()
    except (EOFError, KeyboardInterrupt):
        # Ctrl-C, Ctrl-D, or stdin that is not a terminal.
        print("\n❌ Cancelled. Nothing was saved.")
        return 1

    if not response:
        print("❌ Nothing entered.")
        return 1

    try:
        if response.startswith("http://") or response.startswith("https://"):
            flow.fetch_token(authorization_response=response)
        else:
            # Tolerate a bare code, in case the URL got mangled in transit.
            flow.fetch_token(code=response)
    except Exception as e:
        print(f"\n❌ Could not exchange that for a token: {e}")
        print("\nCommon causes:")
        print("  - The code was already used. Each one works exactly once;")
        print("    re-run this script to get a fresh URL.")
        print("  - More than a few minutes passed. Codes expire quickly.")
        print("  - Only part of the URL was copied. It must include the state")
        print("    parameter as well as the code.")
        return 1

    creds = flow.credentials
    if not creds.refresh_token:
        print("\n⚠️  Google returned no refresh token, so this will stop working")
        print("   in about an hour. Revoke the app's access at")
        print("   https://myaccount.google.com/permissions and run this again.")

    manager.credentials_dir.mkdir(parents=True, exist_ok=True)
    manager.token_file.write_text(creds.to_json())
    manager.token_file.chmod(0o600)

    print(f"\n✅ Token written to {manager.token_file}")

    user_info = manager.get_user_info()
    if user_info:
        print(f"✅ Verified: {user_info.get('name')} ({user_info.get('email')})")
    else:
        print("⚠️  Token saved, but the verification call failed. Check that the")
        print("   Drive, Gmail, Calendar and People APIs are enabled.")

    print("\nThe server will pick this up automatically. No further setup needed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="One-time OAuth2 setup for headless machines.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--force", action="store_true",
                        help="replace an existing token instead of refusing")
    parser.add_argument("--status", action="store_true",
                        help="report current credentials and exit")
    args = parser.parse_args()

    if find_service_account_key() and not args.status:
        print(f"A service account key is already in place at {find_service_account_key()}.")
        print("The server will use it and ignore any OAuth token, so this helper")
        print("has nothing to do. Remove the key first if you want OAuth instead.")
        return 0

    try:
        manager = build_auth_manager()
    except ValueError:
        print("❌ GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are not set.")
        print("   Copy .env.example to .env and fill them in - see docs/setup.md.")
        return 1

    if args.status:
        return show_status(manager)

    if manager.token_file.exists() and not args.force:
        print(f"A token already exists at {manager.token_file}.")
        print("Run with --force to replace it, or --status to check whether it works.")
        return 1

    return run_manual_flow(manager)


if __name__ == "__main__":
    sys.exit(main())
