#!/usr/bin/env python3
"""Create a disposable local IRIS operator for the contest demo."""

import os
import secrets
import subprocess
import sys

container = os.environ.get("IRIS_CONTAINER", "iris-anvil-iris")
password = secrets.token_urlsafe(30)
script = (
    'zn "%SYS"\n'
    'if ##class(Security.Users).Exists("AnvilDemo") { write "ALREADY_EXISTS",! } '
    'else { kill u set u("Roles")="%All",u("Password")="' + password + '",'
    'u("Enabled")=1,u("AccountNeverExpires")=1,u("PasswordNeverExpires")=1 '
    'set sc=##class(Security.Users).Create("AnvilDemo",.u) '
    'write "CREATE_OK=",$SYSTEM.Status.IsOK(sc),! }\n'
    'halt\n'
)
run = subprocess.run(
    ["docker", "exec", "-i", container, "iris", "session", "IRIS"],
    input=script, text=True, capture_output=True, check=False,
)
if run.returncode != 0 or "CREATE_OK=1" not in run.stdout:
    reason = "AnvilDemo already exists" if "ALREADY_EXISTS" in run.stdout else "IRIS user creation failed"
    sys.exit(reason + "; use an existing authorized account or a fresh demo container")
print("Local demo only: AnvilDemo has the %All role in this IRIS container.")
print("ANVIL_OPERATOR_USER=AnvilDemo")
print("ANVIL_OPERATOR_PASSWORD=" + password)
