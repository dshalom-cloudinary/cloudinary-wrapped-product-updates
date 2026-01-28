"""GitHub API client wrapper with authentication."""

import os
import time
from typing import Any

import requests
from github import Github, Auth
from github.GithubException import GithubException
from dotenv import load_dotenv
from rich.console import Console

from .device_auth import authenticate_with_device_flow, DeviceFlowError

# GitHub GraphQL API endpoint
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

# GraphQL retry settings
GRAPHQL_MAX_RETRIES = 3
GRAPHQL_INITIAL_BACKOFF = 1.0  # seconds
GRAPHQL_TIMEOUT = 60  # seconds


class GitHubClient:
    """Wrapper around PyGithub for fetching contribution data."""

    def __init__(self, token: str | None = None, console: Console | None = None):
        """
        Initialize the GitHub client.

        Args:
            token: GitHub Personal Access Token. If not provided,
                   will attempt to load from GITHUB_TOKEN env var,
                   then fall back to Device Flow OAuth.
            console: Rich console for Device Flow output.
        """
        load_dotenv()

        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            # No token provided, use Device Flow
            try:
                self.token = authenticate_with_device_flow(console=console)
            except DeviceFlowError as e:
                raise ValueError(str(e))

        auth = Auth.Token(self.token)
        self.client = Github(auth=auth)
        self._user = None

    @property
    def user(self):
        """Get the authenticated user (cached)."""
        if self._user is None:
            self._user = self.client.get_user()
        return self._user

    @property
    def username(self) -> str:
        """Get the authenticated user's login name."""
        return self.user.login

    def get_org_repos(self, org_name: str) -> list:
        """
        Get all repositories for an organization.

        Args:
            org_name: The organization name.

        Returns:
            List of repository objects.
        """
        try:
            org = self.client.get_organization(org_name)
            return list(org.get_repos())
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"Organization '{org_name}' not found or not accessible.")
            raise

    def get_repo(self, org_name: str, repo_name: str):
        """
        Get a specific repository by org and name.

        Args:
            org_name: The organization name.
            repo_name: The repository name.

        Returns:
            Repository object.

        Raises:
            ValueError: If the repository is not found or not accessible.
        """
        try:
            return self.client.get_repo(f"{org_name}/{repo_name}")
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"Repository '{org_name}/{repo_name}' not found or not accessible.")
            raise

    def verify_connection(self) -> bool:
        """
        Verify that the GitHub connection works.

        Returns:
            True if connection is successful.

        Raises:
            ValueError: If authentication fails.
        """
        try:
            _ = self.username
            return True
        except GithubException as e:
            raise ValueError(f"GitHub authentication failed: {e.data.get('message', str(e))}")

    def execute_graphql(
        self, query: str, variables: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query against GitHub's API with retry logic.

        Args:
            query: The GraphQL query string.
            variables: Optional dictionary of query variables.

        Returns:
            The 'data' portion of the GraphQL response.

        Raises:
            requests.HTTPError: If the request fails after all retries.
            ValueError: If the response contains GraphQL errors.
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        last_exception = None
        backoff = GRAPHQL_INITIAL_BACKOFF
        
        for attempt in range(GRAPHQL_MAX_RETRIES):
            try:
                response = requests.post(
                    GITHUB_GRAPHQL_URL,
                    headers=headers,
                    json=payload,
                    timeout=GRAPHQL_TIMEOUT,
                )
                response.raise_for_status()

                result = response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    error_messages = [e.get("message", str(e)) for e in result["errors"]]
                    raise ValueError(f"GraphQL errors: {'; '.join(error_messages)}")

                return result.get("data", {})
                
            except (requests.RequestException, requests.exceptions.ChunkedEncodingError) as e:
                last_exception = e
                if attempt < GRAPHQL_MAX_RETRIES - 1:
                    # Wait before retrying with exponential backoff
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("GraphQL request failed unexpectedly")

    def close(self):
        """Close the GitHub client connection."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
