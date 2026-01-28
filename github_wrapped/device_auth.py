"""GitHub Device Flow OAuth authentication."""

import time
import webbrowser
import requests
from rich.console import Console

# GitHub OAuth App credentials
GITHUB_CLIENT_ID = "Ov23liTzk9ELYZzdw736"

DEVICE_CODE_URL = "https://github.com/login/device/code"
ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
DEVICE_VERIFICATION_URL = "https://github.com/login/device"

# Scopes needed to read repos, PRs, commits, and reviews
SCOPES = "repo read:org"


class DeviceFlowError(Exception):
    """Error during device flow authentication."""
    pass


def request_device_code(client_id: str = GITHUB_CLIENT_ID) -> dict:
    """
    Request a device code from GitHub.
    
    Returns:
        dict with device_code, user_code, verification_uri, expires_in, interval
    """
    response = requests.post(
        DEVICE_CODE_URL,
        data={
            "client_id": client_id,
            "scope": SCOPES,
        },
        headers={"Accept": "application/json"},
    )
    
    if response.status_code != 200:
        raise DeviceFlowError(f"Failed to get device code: {response.text}")
    
    return response.json()


def poll_for_token(device_code: str, interval: int, expires_in: int, 
                   client_id: str = GITHUB_CLIENT_ID, console: Console | None = None) -> str:
    """
    Poll GitHub for the access token after user authorizes.
    
    Args:
        device_code: The device code from request_device_code
        interval: Polling interval in seconds
        expires_in: How long until the code expires
        client_id: GitHub OAuth App client ID
        console: Rich console for output
        
    Returns:
        Access token string
    """
    start_time = time.time()
    
    while time.time() - start_time < expires_in:
        response = requests.post(
            ACCESS_TOKEN_URL,
            data={
                "client_id": client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        
        data = response.json()
        
        if "access_token" in data:
            return data["access_token"]
        
        error = data.get("error")
        
        if error == "authorization_pending":
            # User hasn't authorized yet, keep polling
            time.sleep(interval)
        elif error == "slow_down":
            # We're polling too fast, increase interval
            interval += 5
            time.sleep(interval)
        elif error == "expired_token":
            raise DeviceFlowError("The device code has expired. Please try again.")
        elif error == "access_denied":
            raise DeviceFlowError("Authorization was denied by the user.")
        else:
            raise DeviceFlowError(f"Authentication error: {error} - {data.get('error_description', '')}")
    
    raise DeviceFlowError("Authentication timed out. Please try again.")


def authenticate_with_device_flow(console: Console | None = None, 
                                   client_id: str = GITHUB_CLIENT_ID) -> str:
    """
    Perform the complete device flow authentication.
    
    Args:
        console: Rich console for pretty output
        client_id: GitHub OAuth App client ID
        
    Returns:
        Access token string
    """
    if console is None:
        console = Console()
    
    if client_id == "YOUR_CLIENT_ID":
        raise DeviceFlowError(
            "Device Flow authentication requires a GitHub OAuth App.\n"
            "Please either:\n"
            "  1. Provide a GitHub Personal Access Token via --token or GITHUB_TOKEN env var\n"
            "  2. Register an OAuth App at https://github.com/settings/applications/new\n"
            "     and set the Client ID in device_auth.py"
        )
    
    # Step 1: Request device code
    console.print("\n[cyan]Initiating GitHub authentication...[/cyan]")
    
    try:
        code_data = request_device_code(client_id)
    except requests.RequestException as e:
        raise DeviceFlowError(f"Network error: {e}")
    
    user_code = code_data["user_code"]
    verification_uri = code_data.get("verification_uri", DEVICE_VERIFICATION_URL)
    device_code = code_data["device_code"]
    expires_in = code_data.get("expires_in", 900)
    interval = code_data.get("interval", 5)
    
    # Step 2: Show user the code and URL
    console.print("\n[bold]To authenticate, please:[/bold]")
    console.print(f"  1. Open: [link={verification_uri}]{verification_uri}[/link]")
    console.print(f"  2. Enter code: [bold yellow]{user_code}[/bold yellow]")
    console.print("")
    
    # Try to open browser automatically
    try:
        webbrowser.open(verification_uri)
        console.print("[dim]Browser opened automatically. If it didn't open, use the link above.[/dim]")
    except Exception:
        pass  # Browser opening is optional
    
    console.print("\n[dim]Waiting for authorization...[/dim]")
    
    # Step 3: Poll for token
    try:
        token = poll_for_token(device_code, interval, expires_in, client_id, console)
        console.print("[green]✓[/green] Authentication successful!")
        return token
    except requests.RequestException as e:
        raise DeviceFlowError(f"Network error during authentication: {e}")
