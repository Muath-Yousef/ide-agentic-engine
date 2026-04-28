import pytest
import os
from datetime import datetime, timedelta
from gateway.key_pool import APIKeyPool, KeyPoolConfig, ServiceKeys, APIKey
import yaml

@pytest.fixture
def temp_config_file(tmp_path):
    config_path = tmp_path / "api_keys.yaml"
    data = {
        "services": {
            "gemini": {
                "keys": [
                    {"value": "key1", "status": "active"},
                    {"value": "key2", "status": "active"}
                ]
            }
        }
    }
    with open(config_path, "w") as f:
        yaml.dump(data, f)
    return str(config_path)

def test_get_key(temp_config_file):
    pool = APIKeyPool(config_path=temp_config_file)
    key = pool.get_key("gemini")
    assert key == "key1"

def test_mark_exhausted(temp_config_file):
    pool = APIKeyPool(config_path=temp_config_file)
    # Mark first key as permanently exhausted
    pool.mark_exhausted("gemini", "key1", is_rate_limit=False)
    
    # Next get_key should return key2
    key = pool.get_key("gemini")
    assert key == "key2"
    
    # Mark key2 as cooldown
    pool.mark_exhausted("gemini", "key2", is_rate_limit=True, cooldown_seconds=60)
    
    # Should be no keys available
    key = pool.get_key("gemini")
    assert key is None
