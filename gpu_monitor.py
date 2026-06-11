import paramiko
import time
import sys
import json
import os
import argparse
from datetime import datetime

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def query_gpu(ssh_client):
    stdin, stdout, stderr = ssh_client.exec_command(
        "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader"
    )
    output = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err:
        return None, err
    return output, None


def parse_gpu_line(line):
    parts = [p.strip() for p in line.split(",")]
    index = int(parts[0])
    name = parts[1]
    mem_used = int(parts[2].replace(" MiB", ""))
    mem_total = int(parts[3].replace(" MiB", ""))
    util = int(parts[4].replace(" %", ""))
    return index, name, mem_used, mem_total, util


def print_gpu_status(output, required_mb=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*70}")
    print(f"  GPU Status @ {now}")
    print(f"{'='*70}")
    print(f"  {'GPU':>3}  {'Name':<25} {'Used':>8} / {'Total':>8}  {'Free':>8}  {'Util':>5}")
    print(f"  {'-'*3}  {'-'*25} {'-'*8}   {'-'*8}  {'-'*8}  {'-'*5}")
    for line in output.split("\n"):
        if not line.strip():
            continue
        idx, name, used, total, util = parse_gpu_line(line)
        free = total - used
        mark = ""
        if required_mb and free < required_mb:
            mark = " <-- NEED"
        print(f"  {idx:>3}  {name:<25} {used:>5} MiB / {total:>5} MiB  {free:>5} MiB  {util:>4}%{mark}")
    print(f"{'='*70}")


def check_all_gpus_enough(output, required_mb):
    for line in output.split("\n"):
        if not line.strip():
            continue
        _, _, used, total, _ = parse_gpu_line(line)
        if total - used < required_mb:
            return False
    return True


def connect(host, port, user, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=password, timeout=10)
    return ssh


def mode_monitor(ssh, args):
    queried = 0
    try:
        while args.count == 0 or queried < args.count:
            output, err = query_gpu(ssh)
            if err:
                print(f"Error: {err}")
                time.sleep(args.interval)
                queried += 1
                continue
            print_gpu_status(output)
            queried += 1
            if args.count == 0 or queried < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def mode_wait(ssh, args):
    required_mb = args.wait * 1024
    print(f"Waiting for ALL GPUs to have >= {args.wait} GB free ...")
    print(f"(checking every {args.interval}s, Ctrl+C to abort)\n")
    checked = 0
    try:
        while True:
            output, err = query_gpu(ssh)
            if err:
                print(f"Error: {err}")
                time.sleep(args.interval)
                checked += 1
                continue
            print_gpu_status(output, required_mb)
            checked += 1
            if check_all_gpus_enough(output, required_mb):
                print(f"\n*** GPU memory sufficient! ({args.wait} GB free on each card) ***")
                print(f"*** Checked {checked} times, total wait ~{checked * args.interval}s ***")
                sys.exit(0)
            print(f"  -> Not enough, waiting {args.interval}s ...")
            time.sleep(args.interval)
            checked += 1
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


def main():
    config = load_config()

    parser = argparse.ArgumentParser(description="Remote GPU memory monitor")
    parser.add_argument("--host", default=config.get("host", ""))
    parser.add_argument("--port", type=int, default=config.get("port", 22))
    parser.add_argument("--user", default=config.get("user", ""))
    parser.add_argument("--password", default=config.get("password", ""))
    parser.add_argument("--interval", type=int, default=20, help="Query interval in seconds (default: 20)")
    parser.add_argument("--count", type=int, default=0, help="Number of queries, 0=unlimited (monitor mode)")
    parser.add_argument("--wait", type=int, default=0, help="Wait mode: wait until each GPU has N GB free, then exit 0")
    args = parser.parse_args()

    if not args.host or not args.user or not args.password:
        print("Error: server info not configured.")
        print("Create config.json (see config.example.json), or pass --host/--user/--password.")
        sys.exit(1)

    print(f"Connecting to {args.user}@{args.host}:{args.port} ...")
    try:
        ssh = connect(args.host, args.port, args.user, args.password)
        print("Connected.\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        if args.wait > 0:
            mode_wait(ssh, args)
        else:
            mode_monitor(ssh, args)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
