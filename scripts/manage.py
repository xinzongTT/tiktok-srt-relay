#!/usr/bin/env python3
"""Interactive SRT stream manager for MediaMTX."""

import os
import re
import sys
import secrets
import string
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MEDIAMTX_FILE = BASE_DIR / "mediamtx.yml"
TEMPLATE_FILE = BASE_DIR / "mediamtx.yml.template"
ENV_FILE = BASE_DIR / ".env"
DOCKER_COMPOSE_FILE = BASE_DIR / "docker-compose.yml"

STREAM_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

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

def init_from_template():
    """Initialize mediamtx.yml from template if it doesn't exist."""
    if MEDIAMTX_FILE.exists():
        return True
    if not TEMPLATE_FILE.exists():
        print("  [错误] 找不到 mediamtx.yml.template，无法初始化。")
        return False
    env = load_env()
    content = TEMPLATE_FILE.read_text(encoding="utf-8")
    content = content.replace("__STREAM_PATH__", env.get("STREAM_PATH", "phone"))
    content = content.replace("__SRT_PORT__", env.get("SRT_PORT", "8890"))
    content = content.replace("__SRT_PUBLISH_PASSPHRASE__", env.get("SRT_PUBLISH_PASSPHRASE", "CHANGE_ME"))
    content = content.replace("__SRT_READ_PASSPHRASE__", env.get("SRT_READ_PASSPHRASE", "CHANGE_ME"))
    MEDIAMTX_FILE.write_text(content, encoding="utf-8")
    return True

def backup_file():
    if MEDIAMTX_FILE.exists():
        bak = str(MEDIAMTX_FILE) + ".bak"
        shutil.copy2(MEDIAMTX_FILE, bak)

def parse_yml():
    """Parse mediamtx.yml paths section."""
    if not MEDIAMTX_FILE.exists():
        return {"header_lines": [], "paths": {}}

    text = MEDIAMTX_FILE.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = {"header_lines": [], "paths": {}}
    in_paths = False
    current_path = None
    current_path_lines = []

    for line in lines:
        if not in_paths:
            result["header_lines"].append(line)
            if line.strip().startswith("paths:"):
                in_paths = True
        else:
            stripped = line.strip()
            if stripped.startswith("#") or stripped == "":
                if current_path:
                    current_path_lines.append(line)
                else:
                    result["header_lines"].append(line)
            elif line and line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
                if current_path:
                    result["paths"][current_path] = current_path_lines
                current_path = stripped[:-1].strip()
                current_path_lines = [line]
            elif current_path:
                current_path_lines.append(line)
            else:
                result["header_lines"].append(line)

    if current_path and current_path_lines:
        result["paths"][current_path] = current_path_lines

    return result

def render_yml(parsed):
    """Render mediamtx.yml from parsed data."""
    out = []
    in_paths = False
    for line in parsed["header_lines"]:
        out.append(line)
        if line.strip().startswith("paths:"):
            in_paths = True
            names = list(parsed["paths"].keys())
            if names:
                for name, plines in parsed["paths"].items():
                    if out and out[-1].strip() != "":
                        out.append("")
                    out.extend(plines)
            break
    return "\n".join(out) + "\n"

def add_stream(path_name, parsed, env):
    if path_name in parsed["paths"]:
        return False, f"流 '{path_name}' 已存在。"

    pub_pass = gen_password()
    read_pass = gen_password()
    pub_latency = env.get("SRT_PUBLISH_LATENCY", "500")
    read_latency = env.get("SRT_READ_LATENCY", "500000")

    lines = [
        f"  {path_name}:",
        f"    source: publisher",
        f"    overridePublisher: false",
        f"    maxReaders: 2",
        f'    srtPublishPassphrase: "{pub_pass}"',
        f'    srtReadPassphrase: "{read_pass}"',
    ]
    parsed["paths"][path_name] = lines

    backup_file()
    MEDIAMTX_FILE.write_text(render_yml(parsed), encoding="utf-8")

    public_host = env.get("PUBLIC_HOST", "YOUR_IP")
    srt_port = env.get("SRT_PORT", "8890")

    return True, {
        "name": path_name,
        "pub_pass": pub_pass,
        "read_pass": read_pass,
        "phone_url": f"srt://{public_host}:{srt_port}?streamid=publish:{path_name}&pkt_size=1316&latency={pub_latency}&passphrase={pub_pass}&pbkeylen=16",
        "obs_url": f"srt://{public_host}:{srt_port}?streamid=read:{path_name}&latency={read_latency}&passphrase={read_pass}&pbkeylen=16",
    }

def delete_stream(path_name, parsed):
    if path_name not in parsed["paths"]:
        return False, f"流 '{path_name}' 不存在。"
    del parsed["paths"][path_name]
    backup_file()
    MEDIAMTX_FILE.write_text(render_yml(parsed), encoding="utf-8")
    return True, f"流 '{path_name}' 已删除。"

def list_streams(parsed, env):
    if not parsed["paths"]:
        print("暂无配置的推流。\n")
        return
    public_host = env.get("PUBLIC_HOST", "YOUR_IP")
    srt_port = env.get("SRT_PORT", "8890")
    pub_latency = env.get("SRT_PUBLISH_LATENCY", "500")
    read_latency = env.get("SRT_READ_LATENCY", "500000")
    print(f"\n{'='*60}")
    print(f"  服务器: {public_host}   端口: {srt_port}")
    print(f"  推流延迟: {pub_latency} us   拉流延迟: {read_latency} us")
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
        print(f"    手机推流: srt://{public_host}:{srt_port}?streamid=publish:{name}&pkt_size=1316&latency={pub_latency}&passphrase={pub_pass}&pbkeylen=16")
        print(f"    拉流密码: {read_pass}")
        print(f"    OBS 拉流: srt://{public_host}:{srt_port}?streamid=read:{name}&latency={read_latency}&passphrase={read_pass}&pbkeylen=16")
    print()

def detect_compose_cmd():
    import subprocess
    try:
        subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=5)
        return ["docker", "compose"]
    except Exception:
        pass
    try:
        subprocess.run(["docker-compose", "version"], capture_output=True, timeout=5)
        return ["docker-compose"]
    except Exception:
        pass
    return None

def restart_service():
    import subprocess
    compose_cmd = detect_compose_cmd()
    if not compose_cmd:
        print("错误: 未找到 docker compose 或 docker-compose 命令。\n")
        return
    cmd = compose_cmd + ["-f", str(DOCKER_COMPOSE_FILE), "restart"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR), timeout=60)
        if result.returncode == 0:
            print("服务重启成功。\n")
        else:
            print(f"重启失败:\n{result.stderr}\n")
    except subprocess.TimeoutExpired:
        print("重启超时。\n")

def update_scripts():
    import subprocess
    try:
        r = subprocess.run(["git", "diff", "--quiet"], capture_output=True, cwd=str(BASE_DIR), timeout=10)
        if r.returncode != 0:
            subprocess.run(["git", "checkout", "--", "."], capture_output=True, cwd=str(BASE_DIR), timeout=10)
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, cwd=str(BASE_DIR), timeout=30)
        if result.returncode == 0:
            if "Already up to date" in result.stdout or "Already up-to-date" in result.stdout:
                print("已是最新版本。\n")
            else:
                print("更新成功。\n")
        else:
            print(f"更新失败，请手动 git pull:\n{result.stderr}\n")
    except subprocess.TimeoutExpired:
        print("更新超时，请检查网络。\n")
    except FileNotFoundError:
        print("未找到 git 命令。\n")

def main():
    os.chdir(BASE_DIR)

    if not init_from_template():
        sys.exit(1)

    env = load_env()

    while True:
        try:
            parsed = parse_yml()
            print("\n" + "="*44)
            print("  TikTok SRT 推流管理")
            print("="*44)
            print("  1. 查看所有推流")
            print("  2. 新增一路推流")
            print("  3. 删除一路推流")
            print("  4. 重启中转服务")
            print("  5. 更新脚本 (git pull)")
            print("  6. 退出")
            print()
            choice = input("  请选择 [1-6]: ").strip()

            if choice == "1":
                list_streams(parsed, env)

            elif choice == "2":
                name = input("  流名称 (字母数字下划线, 如 phone2): ").strip()
                if not name:
                    print("  名称不能为空。")
                    continue
                if not STREAM_NAME_RE.match(name):
                    print("  名称只能包含字母、数字、下划线和短横线。")
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
                update_scripts()

            elif choice == "6":
                print("  再见。")
                break

            else:
                print("  无效选择。")
        except KeyboardInterrupt:
            print("\n  再见。")
            break

if __name__ == "__main__":
    main()
