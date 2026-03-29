# just-agentic — Architecture Plan

## Context
- **Product**: SaaS — ขายให้หลายบริษัท (multi-tenant)
- **Scale target**: 1,000–5,000 concurrent users
- **Compliance**: audit log ต้องครบ, data ต้องอยู่ใน region (data residency)

---

## Phase 1 — Scalability ✅ Done
> FastAPI stateless + Redis + Worker Queue

**Goal:**
- Technical : API stateless, Worker pool รัน graph, SSE relay ผ่าน Redis Streams
- Business  : รองรับ 1,000+ concurrent users, deploy ได้โดยไม่ downtime, scale ตาม demand
- Metric    : 1,000 concurrent users, p95 latency < 3s, zero downtime rolling deploy, worker auto-scale ตาม queue depth

**ปัญหาที่แก้:** API process เดียว hold SSE connection + รัน graph → ไม่สามารถ scale horizontal ได้

**สิ่งที่ทำ:**
1. เพิ่ม Redis service ใน docker-compose
2. FastAPI enqueue task → ARQ queue แทนรัน graph โดยตรง
3. Worker process (ARQ) consume queue → รัน LangGraph graph → publish events → Redis Streams
4. FastAPI SSE endpoint relay จาก Redis Streams (stateless, ไม่ tied กับ worker ใด)
5. Client ไม่ต้องเปลี่ยนเลย — SSE events เหมือนเดิมทุกอย่าง

**ไฟล์หลัก:** `worker.py`, `api/redis_client.py`, `api/routers/agent.py`, `graph/state_builder.py`

**ผลลัพธ์:**
- Scale API instance ได้ไม่จำกัด (stateless)
- Scale worker ได้ตาม load (`docker compose scale worker=N`)
- Instance ล่มไม่กระทบ session อื่น
- Redis Streams: ไม่มี event หาย แม้ relay subscribe ช้ากว่า worker

---

## Phase 2 — Tool Execution Security ✅ Done
> แยก Tool Execution ออกจาก Worker process

**Goal:**
- Technical : Tool รันใน isolated container, internal network, resource limit ต่อ call
- Business  : ลูกค้า enterprise ต้องการ security guarantee ก่อน sign contract, ป้องกัน liability จาก malicious tool use
- Metric    : zero server breach, tool timeout enforced, CPU/RAM capped ต่อ call

**ปัญหาที่แก้:** `run_shell` / `execute_python` รันใน container เดียวกับ Worker — bypass blocklist ได้ → ทำลาย server, resource exhaustion

**Option A (ทำแล้ว)** — Resource limits ใน subprocess ทุก call
- `tool_service/executor.py`: `RLIMIT_CPU` / `RLIMIT_AS` / `RLIMIT_FSIZE` / `RLIMIT_NPROC` / `RLIMIT_NOFILE`
- ใช้ผ่าน `preexec_fn` ใน forked child process เท่านั้น (ไม่กระทบ worker process)

**Option B (ทำแล้ว)** — Tool Execution Service แยก container
- `tool_service/main.py`: FastAPI `POST /execute` พร้อม bearer token auth
- Worker → HTTP → Tool Service (docker-internal only)
- Container constraints:
  - `networks: tool-net` (`internal: true` — ออก internet ไม่ได้)
  - `read_only: true` (/app filesystem)
  - `tmpfs: /tmp:size=128m`
  - `deploy.resources.limits: cpus=2, memory=512M`
- `tools/_tool_client.py`: route ผ่าน HTTP เมื่อ `TOOL_SERVICE_URL` set, fallback local เมื่อ dev/test

**ไฟล์หลัก:** `tool_service/`, `tools/_tool_client.py`, `tools/shell.py`, `tools/code_exec.py`, `Dockerfile.tool-service`

**ผลลัพธ์:**
- Server code ไม่ถูกแตะได้ (read-only FS)
- Tool ล่มไม่กระทบ Worker (แยก process + container)
- Memory bomb → `MemoryError` (ไม่กระทบ worker)
- CPU loop → timeout (ไม่กระทบ job อื่น)
- Shell ออก internet ไม่ได้ (internal network)

---

## Phase 3 — Multi-tenancy + Full Isolation
> Ephemeral Sandbox ต่อ session + Data Residency

**Goal:**
- Technical : Sandbox ต่อ session, data แยกต่อ tenant (schema/DB), deploy ได้ต่าง region, audit log ทุก action ครบถ้วน
- Business  : รองรับ enterprise ที่มี compliance requirement (PDPA, GDPR, SOC2), ขายได้ทั้ง บริษัทไทย/EU/US โดยไม่ผิดกฎหมาย data residency
- Metric    : zero cross-tenant data leak, audit log 100% coverage, deploy ได้ใน AWS/GCP region ที่ลูกค้าเลือก, รองรับ 5,000 concurrent users, RTO < 1 hr

**ปัญหาที่แก้:**
- /tmp shared ระหว่าง users → data leak
- Resource fairness — user เดียว block ทั้ง pool
- Workspace collision — หลาย user เขียน path เดียวกัน
- Data residency — ข้อมูลลูกค้าต้องไม่ข้าม region

**สิ่งที่ต้องทำ (เรียงตาม impact/effort):**

| # | Item | Effort | หมายเหตุ |
|---|---|---|---|
| 1 | Rate limiting per user/tenant (Redis) | 1 วัน | กัน abuse ทันที |
| 2 | Priority queue per role (ARQ) | 1 วัน | admin/manager ได้ worker ก่อน |
| 3 | Ephemeral sandbox per session (Docker) | 2-3 วัน | core isolation |
| 4 | Schema per tenant (PostgreSQL) | 1 สัปดาห์ | enterprise data isolation |
| 5 | Audit log pipeline → immutable store | 1 สัปดาห์ | compliance (PDPA/SOC2) |
| 6 | Region-aware deployment (K8s) | 1 เดือน+ | data residency |

---

## Summary

| Phase | เรื่อง | Status | Business Goal | Key Metric |
|---|---|---|---|---|
| 1 | Scalability | ✅ Done | รองรับ 1,000+ users, no downtime deploy | stateless API, worker auto-scale |
| 2 | Tool Security | ✅ Done | ผ่าน enterprise security review | isolated container, no internet, resource limits |
| 3 | Multi-tenancy + Compliance | Pending | ขาย enterprise ได้, PDPA/GDPR ready | 5,000 concurrent, data residency |
