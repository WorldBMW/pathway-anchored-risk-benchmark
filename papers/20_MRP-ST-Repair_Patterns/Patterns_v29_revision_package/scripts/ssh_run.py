#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Run a remote command on the AutoDL server via paramiko (key auth).

Usage:
    python scripts/ssh_run.py "<remote command>" [timeout_seconds]
Example:
    python scripts/ssh_run.py "screen -ls"
"""
import os
import sys
import paramiko

HOST = "connect.weste.seetacloud.com"
PORT = 11887
USER = "root"
PW = "Ifr1rmCCaep7"
KEY = os.path.expanduser(r"~/.ssh/id_ed25519_autodl")


def connect():
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = dict(hostname=HOST, port=PORT, username=USER, timeout=25,
              banner_timeout=30, auth_timeout=30)
    if os.path.exists(KEY):
        kw["key_filename"] = KEY
        kw["look_for_keys"] = False
        kw["allow_agent"] = False
    else:
        kw["password"] = PW
    cli.connect(**kw)
    return cli


def run(cmd, timeout=60):
    cli = connect()
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    cli.close()
    return rc, out, err


if __name__ == "__main__":
    # Usage: ssh_run.py "<cmd>" [timeout]  |  ssh_run.py --file <local_script> [timeout]
    if sys.argv[1] == "--file":
        with open(sys.argv[2], "r", encoding="utf-8") as fh:
            cmd = fh.read()
        timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    else:
        cmd = " ".join(sys.argv[1:])
        timeout = 60
    rc, out, err = run(cmd, timeout=timeout)
    sys.stdout.write(out)
    sys.stderr.write(err if err else "")
    sys.exit(rc)
