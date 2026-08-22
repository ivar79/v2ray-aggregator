import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import urllib.error

from app.github.publisher import GithubPublisher
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
    publisher = GithubPublisher(output_dir=str(valid_output_dir))
    
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        
        mock_response.read.side_effect = [
            json.dumps({"object": {"sha": "old_commit"}}).encode(),
            json.dumps({"tree": {"sha": "old_tree"}}).encode(),
            json.dumps({"sha": "new_tree"}).encode(),
            json.dumps({"sha": "new_commit"}).encode(),
            json.dumps({"object": {"sha": "new_commit"}}).encode()
        ]
        mock_response.status = 200
        
        result = publisher.publish()
        assert result["status"] == "success"
        assert result["commit_sha"] == "new_commit"

@patch('app.github.publisher.get_settings')
def test_missing_token(mock_get_settings, valid_output_dir, mock_settings):
    mock_settings.github_token = ""
    mock_get_settings.return_value = mock_settings
    publisher = GithubPublisher(output_dir=str(valid_output_dir))
    
    with pytest.raises(RuntimeError, match="Publish failed: GitHub token is missing"):
        publisher.publish()

@patch('app.github.publisher.get_settings')
def test_invalid_authentication(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GithubPublisher(output_dir=str(valid_output_dir))
    
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with pytest.raises(RuntimeError, match="Invalid GitHub token or permission denied"):
            publisher.publish()

@patch('app.github.publisher.get_settings')
def test_missing_required_output_file(mock_get_settings, tmp_path, mock_settings):
    mock_get_settings.return_value = mock_settings
    output_dir = tmp_path / "configs"
    output_dir.mkdir()
    (output_dir / "all.txt").write_text("content")
    
    publisher = GithubPublisher(output_dir=str(output_dir))
    with pytest.raises(RuntimeError, match="Required output file vmess.txt is missing"):
        publisher.publish()

@patch('app.github.publisher.get_settings')
def test_secret_detection(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    (valid_output_dir / "all.txt").write_text(f"content\n{mock_settings.github_token}\nmore")
    
    publisher = GithubPublisher(output_dir=str(valid_output_dir))
    with pytest.raises(RuntimeError, match="Security violation"):
        publisher.publish()

@patch('app.github.publisher.get_settings')
def test_unchanged_output(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GithubPublisher(output_dir=str(valid_output_dir))
    
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = MagicMock()
        mock_response.__enter__.return_value = mock_response
        
        mock_response.read.side_effect = [
            json.dumps({"object": {"sha": "old_commit"}}).encode(),
            json.dumps({"tree": {"sha": "same_tree"}}).encode(),
            json.dumps({"sha": "same_tree"}).encode()
        ]
        mock_response.status = 200
        
        result = publisher.publish()
        assert result["status"] == "unchanged"

@patch('app.github.publisher.get_settings')
def test_token_not_leaked_in_exception(mock_get_settings, valid_output_dir, mock_settings):
    mock_get_settings.return_value = mock_settings
    publisher = GithubPublisher(output_dir=str(valid_output_dir))
    
    with patch('app.github.publisher.GithubPublisher._request') as mock_req:
        mock_req.side_effect = Exception(f"Error with {mock_settings.github_token}")
        with pytest.raises(RuntimeError) as exc:
            publisher.publish()
        assert mock_settings.github_token not in str(exc.value)
        assert "***" in str(exc.value)