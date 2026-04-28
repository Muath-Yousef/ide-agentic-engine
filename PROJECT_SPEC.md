# IDE Agentic Engine — Complete Build Blueprint v1.0

## الهدف النهائي بجملة واحدة
محرك CLI بالـ Python يجلس بين المطوّر وأي LLM، يستخدم MCP كـ standard، يُنفّذ العمليات بشكل batch لتوفير 60-90% من التوكنز، ويتحكم في IDE والمشاريع دون واجهة رسومية.

---

## المعمارية الكاملة — 5 طبقات

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 5 — CLI Interface (main entry point)                 │
│  engine.py  →  يستقبل أوامر المستخدم                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  LAYER 4 — Agent Orchestrator                               │
│  orchestrator.py → يدير conversation loop + tool execution  │
│  context_manager.py → يدير نافذة السياق + Prompt Caching    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  LAYER 3 — MCP Gateway (الصمغ الذكي)                        │
│  mcp_gateway.py → يتحدث مع MCP servers                      │
│  batch_executor.py → ينفّذ operations دفعة واحدة            │
│  tool_registry.py → يسجّل كل الأدوات المتاحة                │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  LAYER 2 — MCP Servers (local processes)                    │
│  server_filesystem.py → قراءة/كتابة الملفات                 │
│  server_terminal.py → تنفيذ أوامر + اقتطاع ذكي              │
│  server_git.py → git operations                             │
│  server_ast.py → code skeleton extraction                   │
│  server_project.py → project-specific context               │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│  LAYER 1 — Optimization Layer                               │
│  prompt_cache.py → Redis-based LLM result caching           │
│  token_optimizer.py → output pruning + diff patches         │
│  cost_tracker.py → tracks token usage per session           │
└─────────────────────────────────────────────────────────────┘
```

---

## هيكل الملفات الكامل

```
ide-agentic-engine/
│
├── engine.py                          # Entry point — CLI interface
│
├── core/
│   ├── __init__.py
│   ├── orchestrator.py                # Main agent loop
│   ├── context_manager.py             # Context window management
│   ├── conversation.py                # Multi-turn conversation state
│   └── config.py                      # Loads engine.yaml + .env
│
├── gateway/
│   ├── __init__.py
│   ├── mcp_gateway.py                 # MCP client — talks to all servers
│   ├── batch_executor.py              # THE CORE: batch tool execution
│   ├── tool_registry.py               # Discovers + registers all tools
│   └── connection_pool.py             # Manages multiple MCP connections
│
├── servers/
│   ├── __init__.py
│   ├── filesystem_server.py           # MCP server: file R/W
│   ├── terminal_server.py             # MCP server: shell execution
│   ├── git_server.py                  # MCP server: git operations
│   ├── ast_server.py                  # MCP server: code skeleton
│   ├── search_server.py               # MCP server: grep/search
│   └── project_server.py              # MCP server: project context
│
├── optimization/
│   ├── __init__.py
│   ├── prompt_cache.py                # Redis caching for LLM calls
│   ├── token_optimizer.py             # Diff patches + output pruning
│   ├── context_compressor.py          # Summarize old context
│   └── cost_tracker.py                # Real-time token cost tracking
│
├── providers/
│   ├── __init__.py
│   ├── base_provider.py               # Abstract LLM provider
│   ├── anthropic_provider.py          # Claude API
│   ├── gemini_provider.py             # Gemini API (for SOCROOT)
│   ├── ollama_provider.py             # Local LLM (free)
│   └── router.py                      # Routes tasks to cheapest model
│
├── profiles/
│   ├── socroot.yaml                   # Profile for SOCROOT project
│   ├── default.yaml                   # Generic project profile
│   └── schema.yaml                    # Profile schema definition
│
├── config/
│   ├── engine.yaml                    # Engine configuration
│   ├── mcp_servers.yaml               # MCP servers config
│   └── model_routing.yaml             # Which task → which model
│
├── tests/
│   ├── test_batch_executor.py
│   ├── test_mcp_gateway.py
│   ├── test_token_optimizer.py
│   └── test_orchestrator.py
│
├── justfile                           # Commands runner
├── .env.example
├── pyproject.toml
└── README.md
```

---

## الملفات الحرجة — المواصفات التفصيلية

### 1. `gateway/batch_executor.py` — القلب النابض

**المسؤولية:** تحويل N استدعاءات أدوات منفصلة إلى استدعاء واحد مُجمَّع.

**المنطق الداخلي:**
```
Input: List[ToolCall]  →  [{tool: "read_file", args: {path: "a.py"}}, ...]
Process:
  1. Group by MCP server (filesystem calls together, git calls together)
  2. For each server: send all batch requests in one go
  3. Collect all results
  4. Return as single structured response to LLM
Output: BatchResult → {results: [{tool: "read_file", output: "..."}], ...}
```

**توفير التوكنز:**
- بدون batch: N round-trips → السياق يتراكم N مرة
- مع batch: 1 round-trip → السياق يُرسل مرة واحدة
- توفير = **60-70% من input tokens**

---

### 2. `gateway/mcp_gateway.py` — بوابة MCP

**المسؤولية:** إدارة connections مع كل MCP servers + تنفيذ الـ batch.

---

### 3. `optimization/token_optimizer.py` — موفّر التوكنز

**3 استراتيجيات:**
**A. Diff Patch بدل Rewrite:** توفير 90% output tokens.
**B. Terminal Output Pruning:** توفير 95% for long command outputs.
**C. Code Skeleton (AST):** توفير 95% for file exploration.

---

### 4. `optimization/prompt_cache.py` — Redis Cache

**منطق الـ Cache:**
- Same file reviewed twice = second time free
- Saving = 70-90% for repetitive tasks

---

### 5. `providers/router.py` — الموزّع الذكي

- يوجه المهام للنماذج الأرخص أو الأقوى بناءً على التعقيد.
- Saving = **70% من تكاليف API شهرياً**.

---

### 6. `profiles/socroot.yaml` — البروفايل الخاص بـ SOCROOT

البروفايل الذي يخصص المحرك لمشروع SOCROOT بالملفات والقيود المطلوبة.

---

### 7. `engine.py` — واجهة المستخدم النهائية

أوامر CLI للتفاعل وتشغيل الوكيل.

---

## خارطة الطريق — 4 مراحل

### Phase 0 — Foundation (3 أيام)
المخرجات: pyproject.toml, providers, basic servers, engine.py.

### Phase 1 — Batch Core (3 أيام)
المخرجات: batch_executor.py, tool_registry.py.

### Phase 2 — Optimization (3 أيام)
المخرجات: prompt_cache.py, token_optimizer.py, router.py.

### Phase 3 — SOCROOT Integration (2 أيام)
المخرجات: profiles integration, project context server.
