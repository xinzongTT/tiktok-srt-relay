# TikTok 手机 SRT 中转完整教程

这是一份按本次实测整理的完整落地文档，目标是搭建一套稳定、轻量、可重复的链路：

`中国手机 -> Ubuntu VPS(MediaMTX SRT relay) -> 美国 Windows OBS -> OBS Virtual Camera / 虚拟声卡 -> TikTok LIVE Studio`

这份教程明确采用：

- 服务器：`Ubuntu 22.04 / 24.04`
- 中转：`MediaMTX`
- 手机推流：`Haivision Play Pro`
- 美国端收流：`OBS`
- 开播：`TikTok LIVE Studio`

不会涉及：

- TikTok API
- TikTok stream key 抓取
- VPS 桌面环境
- VPS 上跑 OBS

## 1. 架构图

```mermaid
flowchart LR
    A["中国手机<br/>Haivision Play Pro"] -->|"SRT publish<br/>publish:phone"| B["Ubuntu VPS<br/>MediaMTX"]
    B -->|"SRT read<br/>read:phone"| C["美国 Windows<br/>OBS"]
    C -->|"OBS Virtual Camera"| D["TikTok LIVE Studio"]
    C -->|"VB-Cable / VoiceMeeter"| D
```

## 2. 本次实测环境

- VPS：`154.40.49.108`
- SSH：`root@154.40.49.108:22`
- 项目目录：`/opt/tiktok-srt-relay`
- SRT 监听端口：`8890/udp`
- 流路径：`phone`
- Docker 镜像：`bluenviron/mediamtx:1.18.2`

## 3. 当前可直接使用的连接参数

### 3.1 手机推流参数

推流目标：

```text
Host: 154.40.49.108
Port: 8890
Mode: Caller
Stream ID: publish:phone
Passphrase: Ep4ePKhyAyizZMEGZwn269pC
```

如果客户端支持直接填完整 URL，使用：

```text
srt://154.40.49.108:8890?streamid=publish:phone&pkt_size=1316&latency=500&passphrase=Ep4ePKhyAyizZMEGZwn269pC&pbkeylen=16
```

说明：

- 跨国链路建议 `latency=500`（如仍有 reordered frames 可升至 `1000` 或 `2000`）
- `pkt_size=1316` 建议保留

### 3.2 OBS 拉流参数

OBS `Media Source -> Input`：

```text
srt://154.40.49.108:8890?streamid=read:phone&latency=500000&passphrase=pEXkdpCD9Pef9BGaQXvWH84U&pbkeylen=16
```

`Input Format`：

```text
mpegts
```

说明：

- `latency=500000` 是 `500000 us`，即 `500 ms`
- 如果不稳定，可改成 `1000000` 或 `2000000`

### 3.3 密码区分

- 推流密码：`SRT_PUBLISH_PASSPHRASE`
- 拉流密码：`SRT_READ_PASSPHRASE`

不要混用。

## 4. 服务器安装与部署

### 4.1 一键安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/xinzongTT/tiktok-srt-relay/master/install.sh | sudo bash
```

### 4.2 手动安装

```bash
cd /opt
git clone https://github.com/xinzongTT/tiktok-srt-relay.git tiktok-srt-relay
cd /opt/tiktok-srt-relay
chmod +x scripts/*.sh
bash scripts/setup.sh
```

脚本会自动完成：

- 安装 `docker.io`
- 安装 Docker Compose
- 安装 `ffmpeg`
- 安装 `ufw`
- 安装 `openssl`
- 安装 `python3`
- 安装 `curl`
- 启动并设为开机自启 `docker`
- 从 `.env.example` 生成 `.env`
- 自动生成随机推流/拉流密码
- 渲染 `mediamtx.yml`
- 放行 `22/tcp`
- 放行 `8890/udp`
- 启动 `MediaMTX`

### 4.3 查看状态

```bash
cd /opt/tiktok-srt-relay
bash scripts/status.sh
```

正常应看到：

- `docker ps` 里有 `tiktok-srt-relay`
- 日志里有：

```text
SRT listener opened on :8890 (UDP)
```

- `ss -lunp` 里有 `*:8890`

### 4.4 服务器验收日志

手机推流成功后，正常日志应包含：

```text
is publishing to path 'phone'
```

OBS 拉流成功后，正常日志应包含：

```text
is reading from path 'phone'
```

## 5. 服务器目录与文件作用

- `docker-compose.yml`
  - 使用 Docker Compose 跑 `MediaMTX`
- `mediamtx.yml.template`
  - 配置模板，只启用 SRT
- `.env.example`
  - 环境变量样例
- `scripts/setup.sh`
  - 首次安装与启动
- `scripts/render-config.sh`
  - 从 `.env` 渲染 `mediamtx.yml`
- `scripts/status.sh`
  - 查看容器、日志、监听状态
- `scripts/test-publish.sh`
  - 用 FFmpeg 本机推测试流
- `scripts/test-read.sh`
  - 用 FFmpeg 本机读测试流
- `scripts/manage.py`
  - 交互式多路推流管理（增删改查、查看连接信息、重启）

## 6. MediaMTX 配置要求

当前方案的关键点：

- 只开启 `SRT`
- 关闭 `RTSP / RTMP / HLS / WebRTC / API / metrics / pprof`
- 监听：`8890/udp`
- 流路径：`phone`
- 推流和读流用不同的 `passphrase`
- Docker 采用 `network_mode: host`

## 7. 手机端推荐方案：Haivision Play Pro

### 7.1 为什么选它

本次实测中：

- `Moblin` 能连上，但码流反复出现 `decode errors`
- 切换到 `Haivision Play Pro` 后，已经成功稳定推到 `MediaMTX`

成功日志示例：

```text
stream is available and online, 2 tracks (H264, MPEG-4 Audio)
is publishing to path 'phone'
```

### 7.2 添加推流频道

在 `Haivision Play Pro` 里：

1. 新建频道
2. 模式选择 `Stream`
3. 协议选择 `SRT`
4. 模式选择 `Caller`
5. 填入：

- 地址：`154.40.49.108`
- 端口：`8890`
- 本地端口：`0`
- 加密：打开
- 密码：`Ep4ePKhyAyizZMEGZwn269pC`
- 流 ID：`publish:phone`
- 延迟：`500`

建议频道名可写：

```text
tk
```

### 7.3 手机端推荐编码参数

- Video codec：`H.264`
- Audio codec：`AAC`
- 分辨率：`720x1280`
- FPS：`30`
- Video bitrate：`2500 kbps`
- Audio bitrate：`128 kbps`
- Keyframe interval：`2 秒`

### 7.4 手机端低延迟建议

本次实测中，以下组合已经连续稳定运行、且日志无错误：

- 手机端 `Haivision Play Pro` 延迟：`500`
- OBS 拉流 `latency=500000`

如果不稳定，再逐步提高手机端延迟，例如：

- `1000`
- `2000`

## 8. OBS 设置

### 8.1 添加 SRT 拉流源

1. 打开 `OBS`
2. `Sources` 点击 `+`
3. 选择 `Media Source`
4. 取消 `Local File`
5. `Input` 填：

```text
srt://154.40.49.108:8890?streamid=read:phone&latency=500000&passphrase=pEXkdpCD9Pef9BGaQXvWH84U&pbkeylen=16
```

6. `Input Format` 填：

```text
mpegts
```

### 8.2 OBS 推荐画布

- Base Canvas：`1080x1920` 或 `720x1280`
- Output Resolution：`1080x1920` 或 `720x1280`

### 8.3 OBS 低延迟建议

如果延迟较大，优先调整：

1. OBS 拉流 URL 中的 `latency`
2. 手机端 Haivision 的 `延迟`

推荐值：

- 手机端：`500`
- OBS：`500000 us`

如果不稳再上调：

- 手机端：`1000`、`2000`
- OBS：`1000000` 或 `2000000`

### 8.4 OBS 读流 URL 示例

推荐：

```text
srt://154.40.49.108:8890?streamid=read:phone&latency=500000&passphrase=pEXkdpCD9Pef9BGaQXvWH84U&pbkeylen=16
```

更稳：

```text
srt://154.40.49.108:8890?streamid=read:phone&latency=1000000&passphrase=pEXkdpCD9Pef9BGaQXvWH84U&pbkeylen=16
```

## 9. OBS 音频送入 TikTok LIVE Studio

### 9.1 安装虚拟声卡

Windows 上安装：

- `VB-Cable`
- 或 `VoiceMeeter`

建议优先 `VB-Cable`。

### 9.2 OBS 里设置监听设备

1. 打开：

```text
Settings -> Audio -> Advanced
```

2. `Monitoring Device` 选择：

```text
CABLE Input
```

### 9.3 给媒体源开启监听输出

1. 在 `混音器` 找到手机流对应的媒体源
2. 点小齿轮
3. 打开：

```text
Advanced Audio Properties
```

4. 该媒体源的 `Audio Monitoring` 选择：

```text
Monitor and Output
```

这样 OBS 一边自己输出，一边把音频送入虚拟声卡。

## 10. TikTok LIVE Studio 设置

在 `TikTok LIVE Studio` 中选择：

- 摄像头：`OBS Virtual Camera`
- 麦克风：`CABLE Output`

然后检查：

- 是否能看到 OBS 画面
- 麦克风电平是否跳动
- 声音是否同步

## 11. 低延迟调优建议

### 11.1 延迟来源

整条链路的延迟通常来自：

- 手机端 SRT 延迟
- VPS 中转
- OBS 拉流缓冲
- OBS Virtual Camera
- TikTok LIVE Studio 采集缓冲

### 11.2 实用建议

本次实测成功的一组参数：

- 手机端：`500`
- OBS：`500000 us`
- H.264
- 720x1280
- 30 fps
- 2500-3000 kbps

如果换了网络环境后不稳定：

- 先把手机端升到 `1000`
- 再升到 `2000`
- OBS 再考虑升到 `1000000` 或 `2000000`

## 12. 验收步骤

### 12.1 VPS 侧

```bash
cd /opt/tiktok-srt-relay
bash scripts/status.sh
```

确认：

- `SRT listener opened on :8890`
- `is publishing to path 'phone'`
- `is reading from path 'phone'`

### 12.2 手机端

确认：

- 已开始推流
- 画面、声音都在采集

### 12.3 OBS 侧

确认：

- 能看到实时画面
- 音频电平在跳
- 画面方向正常

### 12.4 TikTok LIVE Studio 侧

确认：

- 能识别 `OBS Virtual Camera`
- 能识别 `CABLE Output`
- 预览正常
- 声音电平正常

## 13. 常见问题排查

### 13.1 VPS 日志提示 `connection is encrypted, but not passphrase is defined in configuration`

原因：

- 手机端密码、流 ID、路径未正确匹配

处理：

- 推流密码必须是：

```text
Ep4ePKhyAyizZMEGZwn269pC
```

- 流 ID 必须是：

```text
publish:phone
```

### 13.2 OBS 黑屏

检查：

- 手机是否已经开始推流
- VPS 是否出现 `is publishing to path 'phone'`
- OBS URL 是否使用了 `read:phone`
- OBS 是否填了 `mpegts`

### 13.3 有画面没声音

检查：

- 手机端音频采集是否开启
- OBS 混音器是否有音频电平
- OBS 是否设置 `Monitor and Output`
- LIVE Studio 是否选了 `CABLE Output`

### 13.4 延迟太大

优先顺序：

1. 手机端降低 SRT 延迟
2. OBS 拉流降低 `latency`
3. 控制码率在 `2500-3000 kbps`
4. 保持 `H264 / 30fps / 2s keyframe`

### 13.5 花屏、卡顿、断流

先做：

- 手机端提升 `延迟`
- OBS 提高拉流 `latency`
- 降码率到 `2500 kbps`
- 保持 `H.264`

### 13.6 如果 Moblin 出现反复 decode errors

本次实测建议：

- 直接切换到 `Haivision Play Pro`

因为 `Moblin` 在本次环境下虽然能 publish，但码流持续出现：

- `decode errors`
- `too many reordered frames`

而 `Haivision Play Pro` 已经验证能正常推流。

## 14. 推荐最终参数

### 手机端

- 协议：`SRT`
- 模式：`Caller`
- 地址：`154.40.49.108`
- 端口：`8890`
- 本地端口：`0`
- 加密：开启
- 密码：`Ep4ePKhyAyizZMEGZwn269pC`
- 流 ID：`publish:phone`
- 延迟：`500`
- 视频编码：`H.264`
- 音频编码：`AAC`
- 分辨率：`720x1280`
- FPS：`30`
- 视频码率：`2500 kbps`
- 音频码率：`128 kbps`

### OBS

- Input：

```text
srt://154.40.49.108:8890?streamid=read:phone&latency=500000&passphrase=pEXkdpCD9Pef9BGaQXvWH84U&pbkeylen=16
```

- Input Format：`mpegts`
- 画布：竖屏
- 启用 `OBS Virtual Camera`
- 音频走 `VB-Cable`

### TikTok LIVE Studio

- 摄像头：`OBS Virtual Camera`
- 麦克风：`CABLE Output`

## 15. 建议保留的服务器命令

查看状态：

```bash
cd /opt/tiktok-srt-relay
bash scripts/status.sh
```

重渲染配置：

```bash
bash scripts/render-config.sh
```

重启中转：

```bash
docker compose restart
```

实时看日志：

```bash
docker logs -f tiktok-srt-relay
```
