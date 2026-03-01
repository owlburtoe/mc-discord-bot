import pytest
from unittest.mock import MagicMock, AsyncMock
from aiohttp import ClientError
from crafty_api import CraftyClient

@pytest.fixture
async def crafty_client():
    client = CraftyClient(url="https://crafty.local/api/v2", token="fake_token")
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_get_stats_success(crafty_client, mocker):
    """Test that successful get_stats resolves correctly."""
    
    mock_response = AsyncMock()
    mock_response.json.return_value = {"status": "ok", "data": {"running": True, "online": 5}}
    mock_response.raise_for_status = MagicMock()
    
    mock_get = mocker.patch("aiohttp.ClientSession.get")
    mock_get.return_value.__aenter__.return_value = mock_response

    result = await crafty_client.get_stats("test-server")
    
    # Verify the URL construction
    mock_get.assert_called_once_with("https://crafty.local/api/v2/servers/test-server/stats", timeout=10)
    
    # Verify parsing
    assert result["data"]["running"] is True
    assert result["data"]["online"] == 5

@pytest.mark.asyncio
async def test_get_stats_failure(crafty_client, mocker):
    """Test that get_stats lets ClientError bubble up."""
    mock_get = mocker.patch("aiohttp.ClientSession.get")
    mock_get.return_value.__aenter__.side_effect = ClientError("API unreachable")

    with pytest.raises(ClientError):
        await crafty_client.get_stats("test-server")

@pytest.mark.asyncio
async def test_run_action_success(crafty_client, mocker):
    """Test run_action returns True for a 200/204 response."""
    mock_response = AsyncMock()
    mock_response.status = 200
    
    mock_post = mocker.patch("aiohttp.ClientSession.post")
    mock_post.return_value.__aenter__.return_value = mock_response

    result = await crafty_client.run_action("test-server", "start_server")
    
    mock_post.assert_called_once_with("https://crafty.local/api/v2/servers/test-server/action/start_server", timeout=10)
    assert result is True

@pytest.mark.asyncio
async def test_run_action_failure(crafty_client, mocker):
    """Test run_action returns False for non-200 responses."""
    mock_response = AsyncMock()
    mock_response.status = 500
    
    mock_post = mocker.patch("aiohttp.ClientSession.post")
    mock_post.return_value.__aenter__.return_value = mock_response

    result = await crafty_client.run_action("test-server", "start_server")
    
    assert result is False
