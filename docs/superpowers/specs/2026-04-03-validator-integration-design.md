# Validator Integration Design

**Date**: 2026-04-03
**Status**: Approved
**Author**: Claude Code

## Overview

将 validator 验证能力集成到现有 `/mine` skill 中，支持 DATA Mining Subnet 的数据质量评估功能。

## Design Decisions

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 任务获取 | WebSocket 推送 | 平台已对 Validator 开放 WS 访问 |
| 代码组织 | 统一 Skill，分层扩展 | 最小侵入性，共享基础设施 |
| 评分引擎 | 两阶段门控 | 先检查一致性，一致才评分 |
| LLM 后端 | OpenClaw CLI | 用户指定 |
| 评审路径 | 双路径支持 | evaluation-tasks + validation-results |
| Staking | 最小值 0 | 先不强制检查 |
| 容错 | WS 指数退避重连 | 无 HTTP fallback |

## File Structure

```
mine/
├── SKILL.md                      # 扩展：添加 validator 命令文档
├── scripts/
│   ├── run_tool.py               # 扩展：添加 validator-* 命令
│   ├── common.py                 # 扩展：添加 validator resolve_* 函数
│   ├── worker_state.py           # 扩展：添加 ValidatorStateStore
│   │
│   │   # ===== 新增 validator 模块 =====
│   ├── validator_runtime.py      # 新增：主事件循环
│   ├── validator_worker.py       # 新增：后台进程管理
│   ├── evaluation_engine.py      # 新增：两阶段评分引擎
│   ├── ws_client.py              # 新增：WebSocket 客户端
│   └── openclaw_llm.py           # 新增：OpenClaw CLI 封装
│
├── lib/
│   └── platform_client.py        # 扩展：添加 validator API 方法
│
└── references/
    ├── api-validator.md          # 新增：Validator API 文档
    └── protocol-validator.md     # 新增：Validator 协议文档
```

### New Files (7)

| 文件 | 职责 | 来源 |
|------|------|------|
| `validator_runtime.py` | 主事件循环：WS 接收 → ACK → 评分 → 上报 | 改编自 validator-skill |
| `validator_worker.py` | 后台进程管理 (start/stop/status) | 新写 |
| `evaluation_engine.py` | 两阶段评分引擎 | 新写 |
| `ws_client.py` | WebSocket 客户端 | 移植自 validator-skill |
| `openclaw_llm.py` | OpenClaw CLI 调用封装 | 新写 |
| `references/api-validator.md` | Validator API 文档 | 复制自 validator-network-operator |
| `references/protocol-validator.md` | Validator 协议文档 | 复制自 validator-network-operator |

### Extended Files (5)

| 文件 | 改动 |
|------|------|
| `run_tool.py` | 添加 validator-init, validator-start, validator-control, validator-doctor 命令 |
| `common.py` | 添加 resolve_validator_id(), resolve_credit_interval() 等函数 |
| `worker_state.py` | 添加 ValidatorStateStore 类 |
| `lib/platform_client.py` | 添加 11 个 validator API 方法 |
| `SKILL.md` | 添加 validator 命令文档 |

## Evaluation Engine

### Two-Phase Gating

```
┌─────────────────────────────────────────────────────────┐
│                   Evaluation Engine                      │
├─────────────────────────────────────────────────────────┤
│  输入:                                                   │
│    - cleaned_data (原始数据/真实来源)                     │
│    - structured_data (miner 提交的结构化数据)             │
│    - schema_fields (数据集 schema)                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  阶段 1: 一致性检查 (LLM)                                 │
│    输出: consistent (true/false) + reason                │
│                     │                                    │
│          ┌──────────┴──────────┐                        │
│          ▼                     ▼                        │
│   [不一致]                [一致]                         │
│      │                        │                         │
│      ▼                        ▼                         │
│  返回:                   阶段 2: 质量评分 (LLM)          │
│  {                         4维评分:                      │
│    verdict: "rejected",     - 完整性 30%                │
│    consistent: false,       - 准确性 40%                │
│    score: 0,                - 类型正确性 15%            │
│    reason: "..."            - 信息充分性 15%            │
│  }                              │                       │
│                                 ▼                       │
│                            返回:                         │
│                            {                            │
│                              verdict: "accepted",       │
│                              consistent: true,          │
│                              score: 0-100               │
│                            }                            │
└─────────────────────────────────────────────────────────┘
```

### Interface

```python
class EvaluationResult:
    verdict: Literal["accepted", "rejected"]
    consistent: bool
    score: int  # 0-100, meaningful only when consistent=True
    reason: str

class EvaluationEngine:
    def evaluate(
        self,
        cleaned_data: str,
        structured_data: dict[str, Any],
        schema_fields: list[dict[str, Any]] | dict[str, Any],
    ) -> EvaluationResult:
        """两阶段评估：一致性检查 → 质量评分"""
```

### LLM Prompts

**Phase 1: Consistency Check**
```
你是数据一致性检查器。判断 miner 提取的结构化数据是否与原始数据一致。

## 原始数据 (source of truth)
{cleaned_data}

## Miner 提取的结构化数据
{structured_json}

## 判断标准
- 一致 = 结构化数据中的值能在原始数据中找到对应信息，且没有明显捏造
- 不一致 = 结构化数据包含原始数据中不存在的信息，或严重歪曲原意

## 输出 (strict JSON)
{
  "consistent": true/false,
  "reason": "简要说明判断理由"
}
```

**Phase 2: Quality Scoring**
```
你是数据质量评分器。对 miner 提取的结构化数据进行质量评分。

## Schema 定义
{schema_json}

## 原始数据
{cleaned_data}

## Miner 提取的结构化数据
{structured_json}

## 评分维度
1. 完整性 (30%): 必填字段是否齐全？
2. 准确性 (40%): 提取的值是否准确？
3. 类型正确性 (15%): 值的类型是否符合 schema？
4. 信息充分性 (15%): 关键信息是否遗漏？

## 输出 (strict JSON)
{
  "completeness": 0-100,
  "accuracy": 0-100,
  "type_correctness": 0-100,
  "sufficiency": 0-100,
  "final_score": 0-100,
  "notes": "评分说明"
}
```

## Platform Client Extensions

### New Methods

```python
class PlatformClient:
    # --- Identity & Application ---
    def get_me(self) -> dict[str, Any]
    def submit_validator_application(self) -> dict[str, Any]
    def get_my_validator_application(self) -> dict[str, Any]

    # --- Ready Pool ---
    def join_ready_pool(self) -> dict[str, Any]
    def leave_ready_pool(self) -> dict[str, Any]

    # --- Evaluation Tasks ---
    def get_evaluation_task(self, task_id: str) -> dict[str, Any]
    def report_evaluation(self, task_id: str, score: int) -> dict[str, Any]

    # --- Validation Results ---
    def create_validation_result(
        self, submission_id: str, verdict: str, score: int,
        comment: str, idempotency_key: str
    ) -> dict[str, Any]
    def list_validation_results(self, **params) -> list[dict[str, Any]]
    def get_validation_result(self, result_id: str) -> dict[str, Any]
```

### API Endpoints

| Method | Endpoint | Permission | Purpose |
|--------|----------|------------|---------|
| GET | `/api/iam/v1/me` | member+ | 查询身份 |
| POST | `/api/iam/v1/validator-applications` | member | 提交申请 |
| GET | `/api/iam/v1/validator-applications/me` | member | 查询申请 |
| POST | `/api/mining/v1/validators/ready` | validator | 进入就绪池 |
| POST | `/api/mining/v1/validators/unready` | validator | 退出就绪池 |
| POST | `/api/mining/v1/heartbeat` | validator | 心跳（共用） |
| GET | `/api/mining/v1/evaluation-tasks/{id}` | validator | 获取任务 |
| POST | `/api/mining/v1/evaluation-tasks/{id}/report` | validator | 上报评分 |
| POST | `/api/core/v1/validation-results` | validator | 直接写评审 |
| GET | `/api/core/v1/validation-results` | validator | 查询列表 |

## Validator Runtime

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     ValidatorRuntime                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐      ┌─────────────────────────────────┐   │
│  │ Heartbeat Thread│      │         Main Thread              │   │
│  │   (daemon)      │      │                                  │   │
│  ├─────────────────┤      │  WebSocket Client                │   │
│  │ every 55s:      │      │  ws://platform/api/mining/v1/ws │   │
│  │  POST /heartbeat│      │                                  │   │
│  │                 │      │  Event Loop:                     │   │
│  │ Updates:        │      │  1. receive() → WSMessage        │   │
│  │  - credit_score │      │  2. send_ack_eval() within 30s   │   │
│  │  - credit_tier  │      │  3. evaluate()                   │   │
│  │  - eligible     │      │  4. report_evaluation()          │   │
│  └─────────────────┘      │  5. wait credit interval         │   │
│                           │  6. rejoin ready pool            │   │
│                           └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Credit Tier Intervals

| Credit Tier | Interval (seconds) |
|-------------|-------------------|
| novice | 120 |
| good | 30 |
| excellent | 10 |

### State Storage

```
output/
├── agent-runs/           # miner state (unchanged)
│   └── _worker_state/
│       └── session.json
│
└── validator-runs/       # validator state (new)
    └── _worker_state/
        └── session.json
```

## CLI Commands

### New Commands

```bash
python scripts/run_tool.py validator-init          # One-command init
python scripts/run_tool.py validator-init --mainnet
python scripts/run_tool.py validator-status        # Check readiness
python scripts/run_tool.py validator-start         # Start background
python scripts/run_tool.py validator-control status
python scripts/run_tool.py validator-control pause
python scripts/run_tool.py validator-control resume
python scripts/run_tool.py validator-control stop
python scripts/run_tool.py validator-doctor        # Diagnose issues
```

### Output Format

**validator-status**
```json
{
  "ready": true,
  "state": "ready",
  "role": "validator",
  "application_status": "approved",
  "user_message": "Validator 环境就绪，可以开始验证。",
  "user_actions": ["Start validation", "Check status"]
}
```

**validator-control status**
```json
{
  "validation_state": "running",
  "session_id": "val-20260403-abc123",
  "pid": 12345,
  "tasks_completed": 42,
  "credit_score": 75,
  "credit_tier": "good",
  "last_task_at": "2026-04-03T15:30:00Z",
  "uptime_seconds": 3600
}
```

## Error Handling

### Signature Protocol Errors (401)

| Code | Meaning | Resolution |
|------|---------|------------|
| `MISSING_HEADERS` | Missing signature headers | Check signer config |
| `INVALID_NONCE` | Bad nonce format | Check nonce generation |
| `FUTURE_TIMESTAMP` | Timestamp in future | Sync system clock |
| `EXPIRED` | Signature expired | Re-sign request |
| `UNTRUSTED_HOST` | Untrusted host | Check wallet authorization |
| `INVALID_SIGNATURE` | Invalid signature | Check private key |
| `SIGNER_MISMATCH` | Signer mismatch | Check wallet address |
| `NONCE_REUSED` | Reused nonce | Ensure unique nonces |

### Business Errors

| Code | Meaning | Resolution |
|------|---------|------------|
| `validator_application_exists` | Already applied | Query application status |
| `role_suspended` | Role suspended | Contact admin |
| `insufficient_stake` | Insufficient stake | Add more stake |
| `validator_capacity_full` | Capacity full | Wait or increase stake |
| `validator_not_ready` | Not in ready pool | Call join_ready_pool |
| `evaluation_task_not_found` | Task not found | Check task_id |
| `task_claim_forbidden` | Cannot claim | Check validator status |

### WebSocket Reconnection

Exponential backoff: 1s → 2s → 4s → ... → 60s max

```python
class WSReconnectPolicy:
    MIN_DELAY = 1
    MAX_DELAY = 60
    MULTIPLIER = 2
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PLATFORM_BASE_URL` | `http://101.47.73.95` | Platform address |
| `VALIDATOR_ID` | `validator-agent` | Validator identifier |
| `OPENCLAW_CLI_PATH` | `openclaw` | OpenClaw CLI path |
| `EVAL_TIMEOUT_SECONDS` | `120` | Single evaluation timeout |
| `VALIDATOR_OUTPUT_ROOT` | `output/validator-runs` | State storage root |

## Implementation Order

1. **Phase 1: Core Infrastructure**
   - `openclaw_llm.py` - LLM call wrapper
   - `evaluation_engine.py` - Two-phase scoring
   - `ws_client.py` - WebSocket client

2. **Phase 2: Platform Integration**
   - Extend `lib/platform_client.py` with validator methods
   - Extend `common.py` with validator resolve functions

3. **Phase 3: Runtime**
   - `validator_runtime.py` - Main event loop
   - `validator_worker.py` - Background process management
   - Extend `worker_state.py` with ValidatorStateStore

4. **Phase 4: CLI & Docs**
   - Extend `run_tool.py` with validator commands
   - Update `SKILL.md`
   - Add `references/api-validator.md`
   - Add `references/protocol-validator.md`

5. **Phase 5: Testing**
   - Unit tests for evaluation_engine
   - Integration tests for WebSocket flow
   - End-to-end smoke test
