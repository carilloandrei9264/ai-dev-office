"""AI Dev Office package. Importing it loads your .env file and applies the Groq workaround."""
from dotenv import load_dotenv

load_dotenv()

from . import compat  # noqa: E402,F401
