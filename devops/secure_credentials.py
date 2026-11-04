# automation/secure_credentials.py
# Secure LinkedIn credential storage using Windows Credential Manager
# Works on Windows 10/11 using DPAPI-backed encrypted storage.
#
# SECURITY (2026-10-02): commands are executed as argument lists with
# shell=False. Never interpolate secrets into a shell command string --
# passwords routinely contain shell metacharacters (&, |, ", $, !),
# which would break the command or allow arbitrary command execution.

import subprocess


def _run_cmd(args: list) -> str:
    """
    Run a command without shell interpretation (no injection risk).
    `args` is a list like ["cmdkey", "/add:Target", "/user:u", "/pass:p"].
    """
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            shell=False
        )
        return result.stdout.strip()
    except Exception as exc:
        print(f"[CredMan] Command failed: {exc}")
        return ""


# ============================================================
# SAVE CREDENTIALS
# ============================================================

def save_linkedin_credentials(email: str, password: str):
    """
    Store LinkedIn credentials securely in Windows Credential Manager.
    Two entries are created:
      - LinkedInEmail
      - LinkedInPassword
    """

    print("[CredMan] Saving LinkedIn credentials securely...")

    out_email = _run_cmd(
        ["cmdkey", "/add:LinkedInEmail", f"/user:{email}", f"/pass:{password}"]
    )

    if "successfully" in out_email.lower():
        print("[CredMan] LinkedIn email credential saved.")
    else:
        print("[CredMan] Failed to save email credential:", out_email)

    out_pass = _run_cmd(
        ["cmdkey", "/add:LinkedInPassword", "/user:LinkedInUser", f"/pass:{password}"]
    )

    if "successfully" in out_pass.lower():
        print("[CredMan] LinkedIn password credential saved.")
    else:
        print("[CredMan] Failed to save password credential:", out_pass)


# ============================================================
# RETRIEVE CREDENTIALS
# ============================================================

def get_linkedin_credentials():
    """
    Retrieve LinkedIn credentials from Windows Credential Manager.
    Returns (email, password) or (None, None) if missing.

    NOTE: `cmdkey /list` never displays stored passwords, so password
    retrieval via CLI parsing is not viable. This function returns the
    stored email; use the Windows Credential Manager UI or the `keyring`
    package if programmatic password retrieval is needed.
    """

    print("[CredMan] Retrieving LinkedIn credentials...")

    out = _run_cmd(["cmdkey", "/list:LinkedInEmail"])

    email = None
    password = None

    in_target_block = False
    for line in out.splitlines():
        if "Target:" in line:
            in_target_block = "LinkedInEmail" in line
            continue
        if in_target_block and "User:" in line:
            email = line.split("User:")[-1].strip()
            break

    if not email:
        print("[CredMan] LinkedIn credentials not found.")
        return None, None

    print("[CredMan] Email credential retrieved (passwords are not readable via cmdkey).")
    return email, password
