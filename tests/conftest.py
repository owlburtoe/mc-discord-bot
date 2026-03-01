import os

# We must mock these environment variables before ANY module imports `config.py`
# so that the global `settings = Settings()` does not crash during test collection.
os.environ["DISCORD_TOKEN"] = "dummy_token_for_tests"
os.environ["CRAFTY_URL"] = "http://dummy.crafty.local"
os.environ["CRAFTY_TOKEN"] = "dummy_crafty_token_for_tests"
