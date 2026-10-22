"""One-time local OAuth login. Needs client_secret.json from Google Cloud (Desktop app).
Prints the refresh token to store as the GOOGLE_REFRESH_TOKEN secret."""
import sys

from .youtube import SCOPES_GMAIL, SCOPES_YT


def main(path="client_secret.json"):
    from google_auth_oauthlib.flow import InstalledAppFlow
    creds = InstalledAppFlow.from_client_secrets_file(path, SCOPES_YT + SCOPES_GMAIL).run_local_server(port=0)
    print("GOOGLE_REFRESH_TOKEN=" + creds.refresh_token)


if __name__ == "__main__":
    main(*sys.argv[1:])
