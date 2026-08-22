import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

from app.github.publisher import GitHubPublisher
from app.config import Settings

@pytest.fixture
def mock_settings():
    return Settings(
        telegram_api_id=12345,
        telegram_api_hash="secret_api_hash",
        telegram_bot_token="secret_bot_token",
        github_token="secret_github_token",
        github_owner="test_owner",
        github_repo="test_repo",
        channel_name="test_channel",
        channel_username="test_username",
        channel_id="123"
    )

@pytest.fixture
def valid_output_dir(tmp_path):
    output_dir = tmp_path / "configs"
    output_dir.mkdir()
    files = ["all.txt", "vmess.txt", "vless.txt", "trojan.txt", 
             "shadowsocks.txt", "hysteria.txt", "hysteria2.txt", 
             "stats.json", "README.md"]
    for f in files:
        (output_dir / f).write_text(f"content of {f}", encoding="utf-8")
    return output_dir

@patch('app.github.publisher.get_settings')
def test_successful_publish(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GitHubPublisher(local_path=valid_output_dir)
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout="success", stderr="")
        
        result = publisher.publish(source_dir=valid_output_dir)
        assert result["success"] is True

@patch('app.github.publisher.get_settings')
def test_missing_token(mock_get_settings, valid_output_dir, mock_settings):
    mock_settings.github_token = ""
    mock_get_settings.return_value = mock_settings
    publisher = GitHubPublisher(local_path=valid_output_dir, github_token="")
    
    with pytest.raises(RuntimeError, match="GitHub token is missing"):
        publisher.publish(source_dir=valid_output_dir)

@patch('app.github.publisher.get_settings')
def test_invalid_authentication(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GitHubPublisher(local_path=valid_output_dir)
    
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = Exception("Invalid GitHub token or permission denied")
        with pytest.raises(Exception, match="Invalid GitHub token or permission denied"):
            publisher.publish(source_dir=valid_output_dir)

@patch('app.github.publisher.get_settings')
def test_missing_required_output_file(mock_get_settings, tmp_path, mock_settings):
    mock_get_settings.return_value = mock_settings
    output_dir = tmp_path / "configs"
    output_dir.mkdir()
    (output_dir / "all.txt").write_text("content")
    
    publisher = GitHubPublisher(local_path=output_dir)
    with pytest.raises(RuntimeError, match="Required output file vmess.txt is missing"):
        publisher.publish(source_dir=output_dir)

@patch('app.github.publisher.get_settings')
def test_secret_detection(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    (valid_output_dir / "configs" / "all.txt").write_text(f"content\n{mock_settings.github_token}\nmore")
    
    publisher = GitHubPublisher(local_path=valid_output_dir)
    with pytest.raises(RuntimeError, match="Security violation"):
        publisher.publish(source_dir=valid_output_dir)

@patch('app.github.publisher.get_settings')
def test_unchanged_output(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GitHubPublisher(local_path=valid_output_dir)
    
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr="")
        
        result = publisher.publish(source_dir=valid_output_dir)
        assert result["success"] is True

@patch('app.github.publisher.get_settings')
def test_token_not_leaked_in_exception(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GitHubPublisher(local_path=valid_output_dir)
    
    with patch('app.github.publisher.GitHubPublisher._run_git_command') as mock_req:
        mock_req.side_effect = Exception(f"Error with {mock_settings.github_token}")
        
        result = publisher.publish(source_dir=valid_output_dir)
        assert mock_settings.github_token not in result["error"]
        assert "***" in result["error"]