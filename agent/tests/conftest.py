import os

# Keep the suite in a predictable environment.
os.environ.setdefault("ENV", "dev")

# Provider plugins (deepgram, openai) validate that an API key is present at
# construction, so build_pool() and any agent boot test need one. CI has no real
# secrets, so seed harmless placeholders (setdefault never overrides a real key).
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("CARTESIA_API_KEY", "test-cartesia-key")
