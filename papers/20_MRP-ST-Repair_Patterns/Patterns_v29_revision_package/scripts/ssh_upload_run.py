#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Upload a local python script to the AutoDL server, run it, return stdout.
Usage:
    python scripts/ssh_upload_run.py scripts/_remote_check.py [timeout_sec]
"""
import sys
import paramiko

HOST = "connect.weste.seetacloud.com"
PORT = 47707
USER = "root"
PW = "ia+pvdX2udI7"


def main():
    local = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    also_upload = sys.argv[3] if len(sys.argv) > 3 else None  # optional 2nd file to upload
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=20)
    sftp = cli.open_sftp()
    remote_name = "/tmp/_remote_" + local.replace("\\", "/").split("/")[-1]
    sftp.put(local, remote_name)
    if also_upload:
        r2 = "/root/autodl-tmp/project/project4_cervix_multimodal/scripts/" + also_upload.replace("\\", "/").split("/")[-1]
        sftp.put(also_upload, r2)
        print(f"uploaded {also_upload} -> {r2}", flush=True)
    sftp.close()
    py = "/root/miniconda3/bin/python"
    stdin, stdout, stderr = cli.exec_command(f"{py} {remote_name}", timeout=timeout)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    cli.close()
    sys.stdout.write(out)
    sys.stderr.write(err if err else "")
    sys.exit(rc)


if __name__ == "__main__":
    main()