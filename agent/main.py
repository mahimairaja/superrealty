"""Container entrypoint (see agent/Dockerfile: ``main.py download-files`` at
build, ``main.py start`` at run; ``main.py console`` / ``dev`` locally).

Delegates to the openrtc pool: ``AgentPool.run()`` calls ``cli.run_app`` on the
pool's worker, so the LiveKit subcommand (start / download-files / console /
dev) is read from argv exactly as before the openrtc migration.
"""

from src.agent import build_pool

if __name__ == "__main__":
    build_pool().run()
