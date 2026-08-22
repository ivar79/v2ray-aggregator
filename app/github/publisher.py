"""
GitHub Publisher Module for V2Ray Aggregator

This module handles publishing generated configuration files to GitHub repositories.
It uses subprocess for Git operations to avoid additional dependencies.
"""

import subprocess
import logging
import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class GitHubPublisher:
    """Handles publishing configuration files to GitHub repositories."""
    
    def __init__(
        self,
        repo_url: Optional[str] = None,
        branch: str = "main",
        local_path: Optional[Path] = None,
        github_token: Optional[str] = None
    ):
        """
        Initialize GitHub Publisher.
        
        Args:
            repo_url: GitHub repository URL (e.g., https://github.com/owner/repo.git)
            branch: Target branch (default: main)
            local_path: Local path for repository clone
            github_token: GitHub personal access token for authentication
        """
        self.repo_url = repo_url or self._build_repo_url()
        self.branch = branch
        self.local_path = local_path or Path("github_repo")
        self.github_token = github_token or settings.github_token
        self.dry_run = settings.dry_run
        
    def _build_repo_url(self) -> str:
        """Build GitHub repository URL from settings."""
        if not all([settings.github_owner, settings.github_repo]):
            raise ValueError("GITHUB_OWNER and GITHUB_REPO must be set in settings")
        
        return f"https://github.com/{settings.github_owner}/{settings.github_repo}.git"
    
    def _run_git_command(self, command: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """
        Run a Git command using subprocess.
        
        Args:
            command: Git command as list of arguments
            cwd: Working directory for the command
            
        Returns:
            CompletedProcess result
            
        Raises:
            subprocess.CalledProcessError: If command fails
        """
        working_dir = cwd or self.local_path
        
        logger.debug(f"Running git command: {' '.join(command)} in {working_dir}")
        
        try:
            result = subprocess.run(
                command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                check=True
            )
            logger.debug(f"Git command output: {result.stdout}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e}")
            logger.error(f"stderr: {e.stderr}")
            raise
    
    def _clone_repository(self) -> None:
        """Clone the GitHub repository to local path."""
        if self.local_path.exists():
            logger.info(f"Repository already exists at {self.local_path}, pulling instead")
            self._run_git_command(["git", "fetch", "origin"])
            self._run_git_command(["git", "checkout", self.branch])
            self._run_git_command(["git", "pull", "origin", self.branch])
        else:
            logger.info(f"Cloning repository from {self.repo_url} to {self.local_path}")
            
            # Use token for authentication if provided
            clone_url = self.repo_url
            if self.github_token:
                clone_url = self.repo_url.replace("https://", f"https://{self.github_token}@")
            
            self._run_git_command(["git", "clone", clone_url, str(self.local_path)])
            self._run_git_command(["git", "checkout", self.branch], cwd=self.local_path)
    
    def _copy_files_to_repo(self, source_dir: Path) -> None:
        """
        Copy generated files to repository directory.
        
        Args:
            source_dir: Source directory containing generated files
        """
        logger.info(f"Copying files from {source_dir} to {self.local_path}")
        
        # Create target directories if they don't exist
        configs_dir = self.local_path / "configs"
        metadata_dir = self.local_path / "metadata"
        
        configs_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy config files
        if (source_dir / "configs").exists():
            for file in (source_dir / "configs").iterdir():
                if file.is_file():
                    shutil.copy2(file, configs_dir / file.name)
                    logger.debug(f"Copied {file.name} to configs/")
        
        # Copy metadata files
        if (source_dir / "metadata").exists():
            for file in (source_dir / "metadata").iterdir():
                if file.is_file():
                    shutil.copy2(file, metadata_dir / file.name)
                    logger.debug(f"Copied {file.name} to metadata/")
        
        # Copy README if exists
        readme_source = source_dir / "README.md"
        if readme_source.exists():
            shutil.copy2(readme_source, self.local_path / "README.md")
            logger.debug("Copied README.md")
    
    def _commit_changes(self, message: str) -> None:
        """
        Stage and commit changes to Git.
        
        Args:
            message: Commit message
        """
        logger.info("Staging changes")
        self._run_git_command(["git", "add", "."])
        
        # Check if there are changes to commit
        result = self._run_git_command(["git", "status", "--porcelain"])
        if not result.stdout.strip():
            logger.info("No changes to commit")
            return
        
        logger.info(f"Committing changes: {message}")
        self._run_git_command(["git", "commit", "-m", message])
    
    def _push_changes(self) -> None:
        """Push changes to remote repository."""
        logger.info(f"Pushing changes to {self.branch}")
        
        # Configure Git user if not set
        try:
            self._run_git_command(["git", "config", "user.email", "v2ray-aggregator@bot.local"])
            self._run_git_command(["git", "config", "user.name", "V2Ray Aggregator Bot"])
        except subprocess.CalledProcessError:
            logger.warning("Failed to configure Git user, using existing config")
        
        self._run_git_command(["git", "push", "origin", self.branch])
    
    def publish(
        self,
        source_dir: Path,
        commit_message: Optional[str] = None
    ) -> dict:
        """
        Publish generated files to GitHub repository.
        
        Args:
            source_dir: Directory containing generated files
            commit_message: Custom commit message (auto-generated if not provided)
            
        Returns:
            Dictionary with publish results:
            - success: bool
            - commit_hash: Optional[str]
            - error: Optional[str]
        """
        result = {
            "success": False,
            "commit_hash": None,
            "error": None
        }
        
        if self.dry_run:
            logger.info("DRY RUN: Skipping GitHub publish")
            result["success"] = True
            result["error"] = "Skipped (dry run)"
            return result
        
        try:
            # Generate commit message if not provided
            if not commit_message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                commit_message = f"Update configs — {timestamp}"
            
            # Clone or update repository
            self._clone_repository()
            
            # Copy generated files
            self._copy_files_to_repo(source_dir)
            
            # Commit changes
            self._commit_changes(commit_message)
            
            # Get commit hash
            try:
                hash_result = self._run_git_command(["git", "rev-parse", "HEAD"])
                result["commit_hash"] = hash_result.stdout.strip()
                logger.info(f"Commit hash: {result['commit_hash']}")
            except subprocess.CalledProcessError:
                logger.warning("Failed to get commit hash")
            
            # Push changes
            self._push_changes()
            
            result["success"] = True
            logger.info("Successfully published to GitHub")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed: {e.stderr if e.stderr else str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
            
        except Exception as e:
            error_msg = f"Publish failed: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
        
        return result
    
    def cleanup(self) -> None:
        """Clean up local repository clone."""
        if self.local_path.exists():
            logger.info(f"Cleaning up local repository at {self.local_path}")
            try:
                shutil.rmtree(self.local_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup local repository: {e}")