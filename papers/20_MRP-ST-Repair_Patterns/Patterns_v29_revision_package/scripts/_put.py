#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Minimal SFTP uploader to the AutoDL server.

Usage:  python scripts/_put.py <local_file> <remote_abs_path>
"""
import sys
import paramiko

HOST = "connect.weste.seetacloud.com"
PORT = 31716
USER = "root"
PW = "QTCSJgmzZrNP"


def main():
    local, remote = sys.argv[1], sys.argv[2]
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(HOST, port=PORT, username=USER, password=PW, timeout=30)
    sftp = cli.open_sftp()
    sftp.put(local, remote)
    print("put", local, "->", remote, "size", sftp.stat(remote).st_size, flush=True)
    sftp.close()
    cli.close()


if __name__ == "__main__":
    main()
