---
name: mine
description: Agent-first mining skill for signed platform work, crawler execution, and submission export through awp-wallet.
bootstrap: ./scripts/bootstrap.sh
windows_bootstrap: ./scripts/bootstrap.cmd
smoke_test: ./scripts/smoke_test.py
requires:
  bins:
    - npm
    - git
  anyBins:
    - python
    - python3
    - py
---

# Mine

面向 agent 的本地 mining skill 入口。OpenClaw 和其他 **plugin host** 应从仓库根目录加载这份 skill。

核心原则：

- 优先理解用户意图，再执行内部命令
- 对用户返回动作语义，不要默认把底层命令直接抛给用户
- 把 `scripts/run_tool.py` 视为内部控制层，不是对话层 UX
- 默认走 host-friendly 背景挖矿链路，不优先暴露低层 worker 命令

## Agent Actions

这个 skill 对外提供的标准动作是：

| 动作 | 适用场景 | 期望结果 |
| ----- | -------- | -------- |
| `Initialize` | 首次使用、环境未初始化、钱包不可用 | 安装依赖、准备 wallet、完成初始化 |
| `CheckReadiness` | 用户问“能不能开始”“现在状态如何” | 返回 readiness 状态和下一步动作 |
| `StartMining` | 用户要开始挖矿 | 进入后台挖矿会话 |
| `CheckStatus` | 用户问进度、当前状态、是否在跑 | 返回当前 session / epoch / action |
| `PauseMining` | 用户要暂停 | 暂停当前挖矿会话 |
| `ResumeMining` | 用户要继续 | 恢复已暂停会话 |
| `StopMining` | 用户要停止 | 结束会话并保留摘要 |
| `Diagnose` | 用户说出错、401、无法启动、状态异常 | 返回结构化诊断和修复建议 |

对用户的表达优先使用这些动作名或自然语言，例如：

- “初始化挖矿环境”
- “检查是否已就绪”
- “开始挖矿”
- “查看状态”
- “暂停挖矿”
- “继续挖矿”
- “停止挖矿”
- “诊断问题”

只有在用户明确要底层命令、或 host 需要执行映射时，才使用内部命令映射。

## Preferred Flow

标准对话流：

1. 先执行 `CheckReadiness`
2. 如果未初始化，执行 `Initialize`
3. 初始化完成后再次执行 `CheckReadiness`
4. 就绪后执行 `StartMining`
5. 后续统一通过 `CheckStatus` / `PauseMining` / `ResumeMining` / `StopMining` 控制

如果用户只是问“现在能不能挖”或“帮我看看状态”，不要直接启动，先走 `CheckReadiness` 或 `CheckStatus`。

## Readiness States

`CheckReadiness` 和 `Diagnose` 共享统一 readiness 语义：

| State | can_diagnose | can_start | can_mine | Meaning |
| ----- | ------------ | --------- | -------- | ------- |
| `ready` | true | true | true | 完全可用 |
| `registration_required` | true | true | false | 可启动，启动时会自动注册 |
| `auth_required` | true | false | false | wallet session 缺失或过期 |
| `agent_not_initialized` | false | false | false | awp-wallet 或 runtime 尚未准备好 |
| `degraded` | true | true | false | 部分功能可用，但不完整 |

常见 warning：

- `wallet session expired`
- `wallet session expires in Ns`
- `using fallback signature config`

## Behavior Rules

1. 默认优先使用后台会话链路，不要优先调用低层 `run-worker`
2. 默认优先返回“当前状态 + 下一步动作”，而不是一串命令
3. 当 runtime 返回 `selection_required` 时，把它解释为“需要用户选择 dataset”，不要伪造选择
4. 当 runtime 返回 `auth_required` 或 `401`，优先走 `Diagnose` 或 `Initialize`
5. `StopMining` 是有副作用动作，如用户语义不明确，先确认再停
6. 浏览器登录或 LinkedIn 自动登录只在对应场景下启用，不是本 skill 的全局前置条件

## Internal Command Mapping

下面这些是 host / agent 内部映射，不建议直接作为对用户的主要输出：

| 动作 | 内部命令 |
| ---- | -------- |
| `Initialize` | `python scripts/run_tool.py init` |
| `CheckReadiness` | `python scripts/run_tool.py agent-status` |
| `StartMining` | `python scripts/run_tool.py agent-start` |
| `CheckStatus` | `python scripts/run_tool.py agent-control status` |
| `PauseMining` | `python scripts/run_tool.py agent-control pause` |
| `ResumeMining` | `python scripts/run_tool.py agent-control resume` |
| `StopMining` | `python scripts/run_tool.py agent-control stop` |
| `Diagnose` | `python scripts/run_tool.py doctor` |

扩展能力仍然存在，但属于高级或专项能力，不应覆盖上面的主动作契约。例如：

- `process-task-file`
- `export-core-submissions`
- `run-worker`
- `agent-run`
- `first-load`
- `list-datasets`

## Bootstrap

Bootstrap 负责安装依赖、准备 `awp-wallet`、建立本地 wallet session。

- Unix: `./scripts/bootstrap.sh`
- Windows: `./scripts/bootstrap.cmd`

如果 host 支持 platform-specific bootstrap，优先走 frontmatter 中的 `bootstrap` / `windows_bootstrap` 字段，而不是在对话里要求用户手工敲命令。

## Environment (defaults work)

```bash
PLATFORM_BASE_URL=http://101.47.73.95   # testnet default
MINER_ID=mine-agent                      # default
AWP_WALLET_BIN=awp-wallet               # auto-detected
```

EIP-712 signature config is auto-fetched from platform; falls back to built-in defaults if unreachable.

## Optional Capability

`auto-browser` 只在 LinkedIn / 浏览器登录等需要本地可见浏览器接管的场景下使用。它不是本 skill 的全局硬依赖，不应阻塞通用 mining 初始化、状态检查或后台运行。

## Reference

- [`docs/AGENT_GUIDE.md`](./docs/AGENT_GUIDE.md)
- [`docs/ENVIRONMENT.md`](./docs/ENVIRONMENT.md)
- [`README.md`](./README.md)
