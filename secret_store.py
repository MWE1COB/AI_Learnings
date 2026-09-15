"""Encrypts secrets (e.g. the AOAI API key) at rest using the Windows Data
Protection API (DPAPI), scoped to the current Windows user account + machine.

Uses ctypes only (no extra pip dependency). A value encrypted with encrypt()
can only be decrypted by the same Windows user on the same machine, so
copying/sharing the .env file (or the whole project folder) does not leak
the underlying secret — the recipient must enter their own key.

NOTE: plain DPAPI CRYPTPROTECT_UI_FORBIDDEN with no entropy is *not* enough
on domain-joined machines: Windows backs up each user's DPAPI master key to
the domain controller, so the same domain account can transparently decrypt
the ciphertext on any other domain-joined machine too. To actually bind the
secret to this one machine, we mix in this machine's MachineGuid (registry,
not part of the roaming profile) as CryptProtectData's "optional entropy".
"""
import base64
import ctypes
import ctypes.wintypes as wt
import hashlib
import os

_PORTABLE_PREFIX = "penc:"
# Baked into the app on purpose: this makes portable_encrypt/decrypt reversible
# by anyone with the source/exe, so it's obfuscation-at-rest (keeps the key out
# of plain sight in .env), not a secret boundary. Use encrypt()/decrypt() above
# instead when the value must not be recoverable outside this machine.
_PORTABLE_KEY = b"AI_Learnings-DemoQuiz-portable-key-v1"


def _portable_keystream(length: int, nonce: bytes) -> bytes:
    out = b""
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(_PORTABLE_KEY + nonce + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:length]


def portable_encrypt(plain_text: str) -> str:
    """Return an opaque "penc:<base64>" ciphertext that decrypts the same way
    on any machine (unlike encrypt(), which is bound to this user+machine).
    """
    if not plain_text:
        return ""
    data = plain_text.encode("utf-8")
    nonce = os.urandom(8)
    keystream = _portable_keystream(len(data), nonce)
    cipher = bytes(a ^ b for a, b in zip(data, keystream))
    return _PORTABLE_PREFIX + base64.b64encode(nonce + cipher).decode("ascii")


def portable_decrypt(stored_value: str) -> str:
    """Reverse of portable_encrypt(). Returns the value unchanged if it isn't
    portable-encrypted, or "" if decoding fails.
    """
    if not stored_value:
        return ""
    if not stored_value.startswith(_PORTABLE_PREFIX):
        return stored_value
    try:
        raw = base64.b64decode(stored_value[len(_PORTABLE_PREFIX):])
    except Exception:
        return ""
    nonce, cipher = raw[:8], raw[8:]
    keystream = _portable_keystream(len(cipher), nonce)
    data = bytes(a ^ b for a, b in zip(cipher, keystream))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return ""

_ENC_PREFIX = "dpapi:"


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _to_blob(data: bytes) -> _DATA_BLOB:
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _machine_entropy() -> bytes:
    """A per-machine value that doesn't roam with the domain user profile.

    Falls back to the computer name if the registry key is unreadable, which
    is still machine-specific (just easier to spoof than the MachineGuid).
    """
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return guid.encode("utf-8")
    except Exception:
        return os.environ.get("COMPUTERNAME", "unknown-machine").encode("utf-8")


def is_available() -> bool:
    return os.name == "nt"


def encrypt(plain_text: str) -> str:
    """Return an opaque "dpapi:<base64>" ciphertext bound to this user+machine."""
    if not plain_text:
        return ""
    if not is_available():
        return plain_text  # non-Windows: DPAPI unsupported, store as-is
    data_in = _to_blob(plain_text.encode("utf-8"))
    entropy = _to_blob(_machine_entropy())
    data_out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(data_in), None, ctypes.byref(entropy), None, None, 0, ctypes.byref(data_out)
    )
    if not ok:
        raise ctypes.WinError()
    try:
        ciphertext = ctypes.string_at(data_out.pbData, data_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
    return _ENC_PREFIX + base64.b64encode(ciphertext).decode("ascii")


def decrypt(stored_value: str) -> str:
    """Reverse of encrypt(). Returns the plaintext value unchanged if it isn't
    DPAPI-encrypted (legacy/manual .env entries), or "" if decryption fails
    (e.g. the file was copied to a different user/machine).
    """
    if not stored_value:
        return ""
    if not stored_value.startswith(_ENC_PREFIX):
        return stored_value
    if not is_available():
        return ""
    try:
        ciphertext = base64.b64decode(stored_value[len(_ENC_PREFIX):])
    except Exception:
        return ""
    data_in = _to_blob(ciphertext)
    entropy = _to_blob(_machine_entropy())
    data_out = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(data_in), None, ctypes.byref(entropy), None, None, 0, ctypes.byref(data_out)
    )
    if not ok:
        return ""
    try:
        plain = ctypes.string_at(data_out.pbData, data_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(data_out.pbData)
    return plain.decode("utf-8")


def set_env_value(env_path: str, key: str, value: str) -> None:
    """Insert or update a single KEY=VALUE line in a .env file, preserving
    every other line (comments, blank lines, other keys) untouched.
    """
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    prefix = f"{key}="
    for i, line in enumerate(lines):
        if line.startswith(prefix):
            lines[i] = prefix + value
            break
    else:
        lines.append(prefix + value)

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
