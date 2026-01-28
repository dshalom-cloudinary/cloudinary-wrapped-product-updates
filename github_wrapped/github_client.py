"""GitHub API client wrapper with authentication."""

import os
from github import Github, Auth
from github.GithubException import GithubException
from dotenv import load_dotenv


class GitHubClient:
    """Wrapper around PyGithub for fetching contribution data."""

    def __init__(self, token: str | None = None):
        """
        Initialize the GitHub client.

        Args:
            token: GitHub Personal Access Token. If not provided,
                   will attempt to load from GITHUB_TOKEN env var.
        """
        load_dotenv()

        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError(
                "GitHub token not found. Set GITHUB_TOKEN environment variable "
                "or pass token directly."
            )

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

    def close(self):
        """Close the GitHub client connection."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
