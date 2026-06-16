import paramiko
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import json
import os
import sys
from datetime import datetime


CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servers.json")


def load_servers():
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: config file not found: {CONFIG_FILE}")
        print("Copy servers.example.json to servers.json and fill in your server info.")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def _find_chinese_font():
    candidates = [
        'Microsoft YaHei', 'SimHei', 'PingFang SC', 'DengXian',
        'Noto Sans CJK SC', 'Noto Sans SC', 'Source Han Sans SC',
        'WenQuanYi Micro Hei', 'WenQuanYi Zen Hei',
    ]
    for name in candidates:
        try:
            fp = fm.FontProperties(family=name)
            if fp.get_name():
                return fp
        except Exception:
            pass

    for fpath in fm.findSystemFonts():
        try:
            fp = fm.FontProperties(fname=fpath)
            nm = fp.get_name()
            if any(k in nm.lower() for k in ['yahei', 'simhei', 'pingfang', 'dengxian', 'noto sans cjk', 'wenquanyi']):
                return fp
        except Exception:
            pass

    return fm.FontProperties()


def query_gpu(svc):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(svc["host"], port=svc["port"], username=svc["user"], password=svc["password"], timeout=10)
    _, stdout, stderr = ssh.exec_command(
        "nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader"
    )
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    ssh.close()
    if err:
        return None, err
    return out, None


def parse_line(line):
    parts = [p.strip() for p in line.split(",")]
    idx = int(parts[0])
    name = parts[1]
    used = int(parts[2].replace(" MiB", ""))
    total = int(parts[3].replace(" MiB", ""))
    return idx, name, used, total


def collect_all(servers):
    rows = []
    for svc in servers:
        host = svc["host"]
        print(f"  Connecting to {host} ...", end=" ")
        out, err = query_gpu(svc)
        if err:
            print(f"ERROR: {err}")
            continue
        print("OK")
        for line in out.split("\n"):
            if not line.strip():
                continue
            idx, name, used, total = parse_line(line)
            rows.append((host, idx, name, used, total))
    return rows


def draw(rows, output_path):
    font = _find_chinese_font()

    rows.sort(key=lambda r: (r[0], r[1]))
    short_labels = [f"{r[0].split('.')[-1]}:{r[1]}" for r in rows]
    used = [r[3] for r in rows]
    total = [r[4] for r in rows]
    free = [t - u for t, u in zip(total, used)]

    y_pos = range(len(rows))

    fig, ax = plt.subplots(figsize=(10, 0.5 + 0.5 * len(rows)))

    ax.barh(y_pos, free, left=0, color='#4CAF50', label='空闲 (Free)')
    ax.barh(y_pos, used, left=free, color='#F44336', label='已用 (Used)')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(short_labels, fontproperties=font, fontsize=9)

    max_mem = max(total) if total else 1
    ax.set_xlim(0, max_mem * 1.25)

    for i, (u, t, f) in enumerate(zip(used, total, free)):
        pct = u / t * 100 if t else 0
        label_text = f"{u}MiB / {t}MiB ({pct:.0f}%)"
        ax.text(t + max_mem * 0.01, i, label_text, va='center', fontsize=7, fontproperties=font)

    ax.set_xlabel("显存 (MiB)", fontproperties=font)
    ax.set_title(f"GPU 显存占用概览  ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})", fontproperties=font, fontsize=12)
    ax.legend(prop=font, fontsize=9)
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=0.3)

    for side in ['top', 'right']:
        ax.spines[side].set_visible(False)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close(fig)


def main():
    print("=" * 50)
    print("  批量 GPU 显存采集 & 可视化报告")
    print("=" * 50)
    servers = load_servers()
    rows = collect_all(servers)
    if not rows:
        print("No data collected, exiting.")
        sys.exit(1)

    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gpu_report.png")
    draw(rows, output)
    print(f"\nReport saved to: {output}")

    print("\n--- Summary ---")
    for host, idx, name, used, total in rows:
        free = total - used
        pct = used / total * 100
        print(f"  {host.split('.')[-1]}:GPU{idx}  {name}  {used:>5}MiB / {total:>5}MiB  ({pct:.0f}%)")


if __name__ == "__main__":
    main()
