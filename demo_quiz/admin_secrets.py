"""Admin credentials for the demo_quiz app.

Values are stored DPAPI-encrypted (see secret_store.py), so the ciphertext
below is only usable on this Windows account + machine. To change a
password on THIS machine, run this file directly and follow the prompt.

For other users running a shared build of the exe (where the baked-in
ciphertext above won't decrypt for them), set DEMO_ADMIN_PASSWORD /
DEMO_EXPORT_PASSWORD as plaintext in their own .env instead — it gets
encrypted in place on first run, same as BOSCH_AOAI_API_KEY.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import secret_store  # noqa: E402
from runtime_paths import app_dir, secure_file  # noqa: E402

_ENV_PATH = os.path.join(app_dir(), ".env")

ADMIN_PASSWORD_ENC = "dpapi:AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAU+NTlwdrpkajsTZ9W0GV2AAAAAACAAAAAAAQZgAAAAEAACAAAABlIDWBiaYnbqB91SUVHeR7qZL+seqZA4iIx0X7QmZpnwAAAAAOgAAAAAIAACAAAADViZhrgc5PdQcotO6gisXBIg69B8PPJA6yAeNmb4prWhAAAABp5PQuliMIIeQ8T38ankOgQAAAAEDY+mVzCm/xdHGKVkxgymw75j9nni35EWSZnodHsZN+4yLklXkpcaMOS9m8cQdpnXzUp9I0I4GBfgvk2u88KoQ="
EXPORT_PASSWORD_ENC = "dpapi:AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAAU+NTlwdrpkajsTZ9W0GV2AAAAAACAAAAAAAQZgAAAAEAACAAAAC7IZggCsK0hmBnfTs35dU3xqutrAODELgOdecsirpFJQAAAAAOgAAAAAIAACAAAADgiIYwLjdiOenCnD0VIhEc2tgxqaaEJuZC5zhJVTej3BAAAACSNPFy8aaLRgApb3U6V2kjQAAAADC+x9EMQwLUsdtifuAzBLeQynKOhqBZ7Eh7r/N9K1mk9wT81cgzCt8yg0BpQ5AG3BjfWhNqx87jmggg82zXlmY="


def _resolve(env_key: str, baked_in_enc: str) -> str:
    """Prefer a per-machine override from .env; fall back to the baked-in value."""
    override = os.getenv(env_key, "")
    if not override:
        return secret_store.decrypt(baked_in_enc)
    if override.startswith("dpapi:"):
        return secret_store.decrypt(override)
    # Plaintext override: encrypt it in place so it isn't left on disk as-is.
    try:
        secret_store.set_env_value(_ENV_PATH, env_key, secret_store.encrypt(override))
        secure_file(_ENV_PATH)
    except OSError:
        pass
    return override


def get_admin_password() -> str:
    return _resolve("DEMO_ADMIN_PASSWORD", ADMIN_PASSWORD_ENC)


def get_export_password() -> str:
    return _resolve("DEMO_EXPORT_PASSWORD", EXPORT_PASSWORD_ENC)


if __name__ == "__main__":
    import getpass
    admin_pw = getpass.getpass("New admin password (blank = keep current): ").strip()
    export_pw = getpass.getpass("New export password (blank = keep current): ").strip()
    if admin_pw:
        print(f'ADMIN_PASSWORD_ENC = "{secret_store.encrypt(admin_pw)}"')
    if export_pw:
        print(f'EXPORT_PASSWORD_ENC = "{secret_store.encrypt(export_pw)}"')
    print("Paste the printed line(s) above into admin_secrets.py to update.")



if __name__ == "__main__":
    import getpass
    admin_pw = getpass.getpass("New admin password (blank = keep current): ").strip()
    export_pw = getpass.getpass("New export password (blank = keep current): ").strip()
    if admin_pw:
        print(f'ADMIN_PASSWORD_ENC = "{secret_store.encrypt(admin_pw)}"')
    if export_pw:
        print(f'EXPORT_PASSWORD_ENC = "{secret_store.encrypt(export_pw)}"')
    print("Paste the printed line(s) above into admin_secrets.py to update.")
