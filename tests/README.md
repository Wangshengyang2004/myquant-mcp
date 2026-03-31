# Tests

本目录现在包含两类测试：

## 1. 单元测试

默认执行，且不依赖真实 GM / MyQuant 环境。

覆盖重点：

- `server/api/*`
- `server/config.py`
- `server/log_config.py`
- `server/app.py`
- `server/mcp_server.py`

运行方式：

```powershell
.venv\Scripts\python -m pytest
```

## 2. 集成测试

以下脚本会访问真实 GM / MyQuant 能力，因此默认跳过：

- `test_available.py`
- `test_unavailable.py`
- `test_quick_check.py`
- `test_ipo_check.py`

如需执行，先准备好有效的 `.env` 和可访问的 GM 终端，然后：

```powershell
$env:RUN_INTEGRATION_TESTS="1"
.venv\Scripts\python -m pytest
```
