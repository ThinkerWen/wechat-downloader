# 🎬 WeChat Video Downloader | 微信视频号下载器

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/wxw/wechat-downloader?style=social)](https://github.com/ThinkerWen/wechat-downloader)

**一个强大的微信视频号自动下载工具，支持加密视频解密、多格式下载和自动代理设置。**

✨ **这是一个易于二次开发的 Python 版本** - 纯 Python 本地实现、详细的代码注释，是学习和扩展的理想选择。

---

</div>

## ✨ 主要特性

### 功能特性
- 🎯 **自动嗅探**：通过代理自动捕获微信视频号链接
- 🔐 **智能解密**：自动识别并解密加密视频
- 📥 **多格式支持**：支持 M3U8 流媒体和普通 MP4 视频下载
- 🚀 **快速下载**：多线程下载，支持断点续传
- 🔧 **自动配置**：一键设置系统代理（支持 macOS、Windows、Linux）
- 📊 **进度显示**：实时显示下载进度和速度
- 🛡️ **安全稳定**：基于 mitmproxy 的专业代理框架
- ⚡ **零配置体验**：开箱即用，无需复杂配置

## 🚀 快速开始

### 前置要求

- Python 3.10+
- pip / uv 或其他 Python 包管理器
- macOS / Windows / Linux

### 安装

#### UV (推荐 见[uv](https://github.com/astral-sh/uv))

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/wechat-downloader.git
cd wechat-downloader
```

2. **启动**
```bash
uv sync
uv run python main.py
```

#### 本地安装

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/wechat-downloader.git
cd wechat-downloader
```

2**安装依赖**
```bash
pip install -r requirements.txt
```

3**启动**
```bash
python main.py
```

### 用法

#### 场景 1：在线实时下载

1. 运行程序：`python main.py`
2. 打开微信，访问视频号
3. 程序自动下载视频到 `./downloads` 目录
4. 按 `Ctrl+C` 退出

#### 场景 2：自定义下载目录(端口)

```bash
python main.py -d ~/Videos/WeChat_Videos -p 8080
```

#### 场景 3：复杂网络环境

如果需要手动配置代理：
```bash
python main.py --no-auto-proxy
```

然后手动在系统代理设置中填入：
- 地址：`127.0.0.1`
- 端口：程序输出的端口号(默认 8899)

## 🔒 隐私和安全

- ✅ 所有操作均在本地进行
- ✅ 不收集用户信息
- ✅ 仅拦截和解密自己的视频
- ✅ 代理仅在程序运行时有效，退出时自动清理

## 💡 易于二次开发

这是一个专为开发者设计的 Python 版本，具有以下优势：

### 项目架构

```
wechat-downloader/
├── core/                    # 核心模块 - 代理和嗅探逻辑
│   ├── addon_server.py      # mitmproxy 插件入口
│   ├── proxy_addon.py       # 代理拦截和链接嗅探
│   └── proxy_manager.py     # 系统代理管理
├── crypto/                  # 解密模块
│   └── decryptor.py         # 视频解密算法
├── downloaders/             # 下载器模块
│   ├── m3u8_downloader.py   # M3U8 流媒体下载
│   └── video_downloader.py  # MP4 下载
├── models/                  # 数据模型
│   ├── entities.py          # 数据类定义
│   └── exceptions.py        # 异常定义
└── utils/                   # 工具模块
    ├── config.py            # 配置管理
    └── logger.py            # 日志系统
```

### 开发指南

#### 添加新的视频格式支持

在 `downloaders/` 目录下创建新的下载器类，参考现有的 `m3u8_downloader.py` 和 `video_downloader.py` 实现接口。

#### 修改视频识别规则

编辑 `core/proxy_addon.py` 中的视频识别逻辑，添加自定义规则。

#### 扩展解密功能

在 `crypto/decryptor.py` 中添加新的解密算法，支持解密的版本迭代。

## 🐛 常见问题

**Q: 无法连接到代理？**  
A: 首次运行需要安装 mitmproxy 证书。按照程序提示安装证书后重试。

**Q: 代理设置后无法访问网络？**  
A: 程序退出时会自动清理代理。如手动退出未清理，请：
- macOS: System Preferences → Network → Wi-Fi Proxies（清除 HTTP/HTTPS 代理）
- Windows: Settings → Network & Internet → Proxy（关闭代理）

**Q: 支持哪些视频格式？**  
A: 支持 M3U8 流媒体（HLS）和 MP4 格式。加密视频会自动解密。

**Q: 可以同时下载多个视频吗？**  
A: 是的，程序会自动排队并按配置的并发数下载。

**Q: 如何添加自定义的下载格式？**  
A: 参考「易于二次开发」章节，在 `downloaders/` 目录下创建新的下载器类即可。

## 🙏 致谢

部分思路及代码参考自：

- [WechatVideoSniffer2.0](https://github.com/kanadeblisst00/WechatVideoSniffer2.0)
- [WechatSphDecrypt](https://github.com/Hanson/WechatSphDecrypt)

---
本项目采用 [MIT License](LICENSE) - 详见 LICENSE 文件
