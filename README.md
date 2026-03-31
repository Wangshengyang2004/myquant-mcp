# MyQuant MCP Server

基于掘金量化（MyQuant）GM API 的 MCP 服务，提供行情、基本面、账户查询和可选交易能力。

## 两种使用方式

1. 直接把这个服务的 HTTP MCP endpoint 接到客户端。
2. 使用仓库内置 skill，通过 `skills/myquant-mcp/scripts/client.py` 访问只读 REST 数据接口。

## 系统要求

### 1. Windows

推荐优先使用 Windows。

原因：

- 掘金终端只能运行在 Windows 上。
- 如果你希望本机直接运行掘金终端和本项目，Windows 是最简单的部署方式。

适用场景：

- 掘金终端和本项目部署在同一台 Windows 机器上
- 或者本项目部署在任意机器上，但远程连接另一台 Windows 掘金终端

### 2. Ubuntu

Ubuntu 只建议用于部署本项目服务端，不用于运行掘金终端本体。

要求：

- 必须是 `x86_64 / amd64`
- 不建议使用 `arm64`

原因：

- `arm64` 环境下没有可用的 `gm` Python 包
- 掘金终端本身仍然需要运行在 Windows 机器上

部署方式：

- 可直接在 Ubuntu 上用 Python 运行
- 也可以用 Docker / Docker Compose 部署

但无论哪种方式，都必须确保：

- 有一台 Windows PC 正在运行掘金终端
- Ubuntu 机器能够访问这台 Windows PC
- 在 `.env` 中把 `GM_SERV_ADDR` 设置成这台 Windows 机器的地址，例如：

```env
GM_SERV_ADDR=192.168.1.10:7001
```

## 先启动服务

```bash
git clone https://github.com/Wangshengyang2004/myquant-mcp.git
cd myquant-mcp
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python server.py
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python server.py
```

至少配置：

```env
GM_TOKEN=your_gm_token_here
MCP_AUTH_TOKEN=replace_with_a_long_random_value
TRADING_ENABLED=false
```

如果服务端不运行在掘金终端所在的 Windows 机器上，还需要设置：

```env
GM_SERV_ADDR=<运行掘金终端的 Windows 机器 IP>:7001
```

默认 endpoint：

- Web UI: `http://127.0.0.1:8001/`
- MCP: `http://127.0.0.1:8001/mcp/`
- REST: `http://127.0.0.1:8001/api/v1/tools`

## 直接接入 MCP

### 1. Cursor

Cursor 官方文档支持项目级 [`.cursor/mcp.json`](C:\Users\simonwsy\Desktop\Workspace\myquant-mcp\.cursor\mcp.json)，远程 MCP 服务器用 `url` 配置即可。

本仓库已经提供好：

```json
{
  "mcpServers": {
    "myquant-mcp": {
      "url": "http://127.0.0.1:8001/mcp/"
    }
  }
}
```

如果服务不在本机，把 URL 改成你的实际地址，例如 `http://192.168.1.10:8001/mcp/`。

### 2. Claude Code

Claude Code 官方文档支持项目级 [`.mcp.json`](C:\Users\simonwsy\Desktop\Workspace\myquant-mcp\.mcp.json)，HTTP MCP 服务器使用 `type: "http"` 加 `url`。

本仓库已经提供好：

```json
{
  "mcpServers": {
    "myquant-mcp": {
      "type": "http",
      "url": "http://127.0.0.1:8001/mcp/"
    }
  }
}
```

也可以手动添加：

```bash
claude mcp add --transport http myquant-mcp http://127.0.0.1:8001/mcp/
```

如果你的服务跑在别的机器上，把 URL 替换成对应地址。

### 3. OpenClaw

OpenClaw 官方文档支持把兼容 Claude/Cursor 的 bundle 安装成 plugin bundle，并导入 bundle 里的 MCP 配置。这个仓库里已经带了 `.mcp.json` 和 `skills/`。

安装方式：

```bash
openclaw plugins install ./myquant-mcp
openclaw plugins info myquant-mcp
openclaw gateway restart
```

OpenClaw 读取到的 MCP 配置同样应该指向 HTTP endpoint，而不是 `server.py`。也就是说，仓库里的 `.mcp.json` 应该保持为：

```json
{
  "mcpServers": {
    "myquant-mcp": {
      "type": "http",
      "url": "http://127.0.0.1:8001/mcp/"
    }
  }
}
```

如果服务部署在远端，把 URL 改成远端地址。

## Skill 方式

仓库内置 skill 位于：

- [skills/myquant-mcp/SKILL.md](C:\Users\simonwsy\Desktop\Workspace\myquant-mcp\skills\myquant-mcp\SKILL.md)
- [skills/myquant-mcp/scripts/client.py](C:\Users\simonwsy\Desktop\Workspace\myquant-mcp\skills\myquant-mcp\scripts\client.py)

这个 skill 走的是只读 REST 接口，适合行情和基本面查询，不适合账户和交易操作。

这样设计是出于安全考虑：

- 交易 API 暴露给通用 skill 或通用 HTTP 客户端会更脆弱，风险更高
- 因此 skill 方式只提供数据 API，不提供交易能力

示例：

```bash
python skills/myquant-mcp/scripts/client.py --list-tools
python skills/myquant-mcp/scripts/client.py --info history
python skills/myquant-mcp/scripts/client.py history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31
```

## 重要说明

- `TRADING_ENABLED=false` 应保持默认值，除非你明确需要真实交易。
- 账户和交易工具需要 `MCP_AUTH_TOKEN`。
- `skills/myquant-mcp/scripts/client.py` 只调用 REST API，因此不能访问账户和交易工具。

## 项目结构

```text
myquant-mcp/
├── server.py
├── skills/
│   └── myquant-mcp/
│       ├── SKILL.md
│       ├── agents/
│       ├── references/
│       └── scripts/
├── server/
│   ├── api/
│   ├── tools/
│   ├── app.py
│   ├── mcp_server.py
│   └── webui.html
├── tests/
├── .mcp.json
├── .cursor/
│   └── mcp.json
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

## 贡献

贡献说明见 `CONTRIBUTING.md`。

## 安全策略

安全说明和漏洞披露建议见 `SECURITY.md`。

## License

MIT，见 `LICENSE`。
