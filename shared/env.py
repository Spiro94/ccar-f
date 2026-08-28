"""Loads .env into os.environ.

The Agent SDK spawns the `claude` CLI as a subprocess and the Python SDK merges
os.environ into that subprocess's environment. Importing this module before
query() is what puts ANTHROPIC_API_KEY where the CLI can find it, ahead of its
stored OAuth profile.
"""

from dotenv import load_dotenv

load_dotenv()
