#!/usr/bin/env python3
"""Interactive SRT stream manager for MediaMTX."""

import os
import sys
import secrets
import string
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIAMTX_FILE = BASE_DIR / "mediamtx.yml"
ENV_FILE = BASE_DIR / ".env"
DOCKER_COMPOSE_FILE = BASE_DIR / "docker-compose.yml"

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def gen_password(length=24):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

def parse_yml():
    """Parse mediamtx.yml and return structured data."""
    if not MEDIAMTX_FILE.exists():
        return {"global": {}, "paths": {}}

    text = MEDIAMTX_FILE.read_text()
    lines = text.splitlines()

    result = {"global_lines": [], "path_lines": [], "paths": {}, "in_paths": False, "header_lines": []}
    in_paths = False
    current_path = None
    current_path_lines = []
    header_done = False

    for line in lines:
        if line.strip().startswith("paths:"):
            in_paths = True
            result["header_lines"].append(line)
            header_done = True
            continue
        if not in_paths:
            if not header_done:
                result["header_lines"].append(line)
        else:
            stripped = line.strip()
            # detect path key (no leading spaces, ends with colon)
            if line and not line.startswith(" ") and not line.startswith("\t") and line.endswith(":") and stripped != "paths:":
                if current_path:
                    result["paths"][current_path] = current_path_lines
                current_path = stripped[:-1]
                current_path_lines = [line]
            elif current_path:
                current_path_lines.append(line)
            elif stripped.startswith("#"):
                current_path = None
                result["header_lines"].append(line)
            else:
                result["header_lines"].append(line)

    if current_path and current_path_lines:
        result["paths"][current_path] = current_path_lines

    return result

def render_yml(parsed):
    """Render mediamtx.yml from parsed data."""
    lines = list(parsed["header_lines"])
    for name, plines in parsed["paths"].items():
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.extend(plines)
    return "\n".join(lines) + "\n"

def add_stream(path_name, parsed, env):
    if path_name in parsed["paths"]:
        return False, f"流 '{path_name}' 已存在。"

    pub_pass = gen_password()
    read_pass = gen_password()

    lines = [
        f"  {path_name}:",
        f"    source: publisher",
        f"    overridePublisher: false",
        f"    maxReaders: 2",
        f'    srtPublishPassphrase: "{pub_pass}"',
        f'    srtReadPassphrase: "{read_pass}"',
    ]
    parsed["paths"][path_name] = lines

    text = render_yml(parsed)
    MEDIAMTX_FILE.write_text(text)

    public_host = env.get("PUBLIC_HOST", "YOUR_IP")
    srt_port = env.get("SRT_PORT", "8890")

    return True, {
        "name": path_name,
        "pub_pass": pub_pass,
        "read_pass": read_pass,
        "phone_url": f"srt://{public_host}:{srt_port}?streamid=publish:{path_name}&pkt_size=1316&latency=500&passphrase={pub_pass}&pbkeylen=16",
        "obs_url": f"srt://{public_host}:{srt_port}?streamid=read:{path_name}&latency=500000&passphrase={read_pass}&pbkeylen=16",
    }

def delete_stream(path_name, parsed):
    if path_name not in parsed["paths"]:
        return False, f"流 '{path_name}' 不存在。"
    del parsed["paths"][path_name]
    text = render_yml(parsed)
    MEDIAMTX_FILE.write_text(text)
    return True, f"流 '{path_name}' 已删除。"

def list_streams(parsed, env):
    if not parsed["paths"]:
        print("暂无配置的推流。\n")
        return
    public_host = env.get("PUBLIC_HOST", "YOUR_IP")
    srt_port = env.get("SRT_PORT", "8890")
    print(f"\n{'='*60}")
    print(f"  服务器: {public_host}   端口: {srt_port}")
    print(f"{'='*60}")
    for name, plines in parsed["paths"].items():
        pub_pass, read_pass = "", ""
        for line in plines:
            if "srtPublishPassphrase:" in line:
                pub_pass = line.split('"')[1] if '"' in line else line.split(":")[-1].strip()
            if "srtReadPassphrase:" in line:
                read_pass = line.split('"')[1] if '"' in line else line.split(":")[-1].strip()
        print(f"\n  [{name}]")
        print(f"    推流密码: {pub_pass}")
        print(f"    手机推流: srt://{public_host}:{srt_port}?streamid=publish:{name}&pkt_size=1316&latency=500&passphrase={pub_pass}&pbkeylen=16")
        print(f"    拉流密码: {read_pass}")
        print(f"    OBS 拉流: srt://{public_host}:{srt_port}?streamid=read:{name}&latency=500000&passphrase={read_pass}&pbkeylen=16")
    print()

def restart_service():
    import subprocess
    cmd = ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "restart"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    if result.returncode == 0:
        print("服务重启成功。\n")
    else:
        print(f"重启失败:\n{result.stderr}\n")

def main():
    os.chdir(BASE_DIR)
    env = load_env()

    while True:
        parsed = parse_yml()
        print("\n" + "="*44)
        print("  TikTok SRT 推流管理")
        print("="*44)
        print("  1. 查看所有推流")
        print("  2. 新增一路推流")
        print("  3. 删除一路推流")
        print("  4. 重启中转服务")
        print("  5. 退出")
        print()
        choice = input("  请选择 [1-5]: ").strip()

        if choice == "1":
            list_streams(parsed, env)

        elif choice == "2":
            name = input("  流名称 (如 phone2): ").strip()
            if not name:
                print("  名称不能为空。")
                continue
            ok, result = add_stream(name, parsed, env)
            if ok:
                print(f"\n  [OK] 推流 '{result['name']}' 已添加。\n")
                print(f"  推流密码: {result['pub_pass']}")
                print(f"  拉流密码: {result['read_pass']}")
                print(f"\n  手机推流 URL:")
                print(f"  {result['phone_url']}")
                print(f"\n  OBS 拉流 URL:")
                print(f"  {result['obs_url']}")
                r = input("\n  是否立即重启服务？[Y/n]: ").strip().lower()
                if r in ("", "y", "yes"):
                    restart_service()
            else:
                print(f"  [错误] {result}")

        elif choice == "3":
            names = list(parsed["paths"].keys())
            if not names:
                print("  没有可删除的推流。")
                continue
            for i, n in enumerate(names, 1):
                print(f"  {i}. {n}")
            sel = input("  输入序号删除: ").strip()
            try:
                idx = int(sel) - 1
                if idx < 0 or idx >= len(names):
                    print("  无效的序号。")
                    continue
            except ValueError:
                print("  无效输入。")
                continue
            ok, msg = delete_stream(names[idx], parsed)
            if ok:
                print(f"  [OK] {msg}")
                r = input("\n  是否立即重启服务？[Y/n]: ").strip().lower()
                if r in ("", "y", "yes"):
                    restart_service()
            else:
                print(f"  [错误] {msg}")

        elif choice == "4":
            restart_service()

        elif choice == "5":
            print("  再见。")
            break

        else:
            print("  无效选择。")

if __name__ == "__main__":
    main()
