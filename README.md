# Network Route Optimizer

Production-grade network routing API built with **Django 5.2 LTS**, **Django REST Framework** and
**PostgreSQL**. Manage a directed, latency-weighted network graph (nodes and edges) and compute the
**lowest-latency path** between two nodes with **Dijkstra's algorithm**; every successful query is
recorded in a filterable history.

| | |
|---|---|
| Language / framework | Python 3.13, Django 5.2 (LTS), DRF 3.16+ |
| Database | PostgreSQL (psycopg 3 with Django's **native connection pool**) |
| Packaging | [`uv`](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`) |
| Quality gates | ruff, mypy (strict), bandit, gitleaks, hadolint, pytest (≥ 90 % coverage), pip-audit |
| API docs | Postman collection (`postman/`), endpoint reference below |

---

## Table of contents

1. [Setup and test guide](#setup-and-test-guide)
2. [API reference](#api-reference)
3. [Architecture](#architecture)
4. [Database design](#database-design)
5. [Design decisions](#design-decisions-why-this-and-not-that)
6. [Transactions & concurrency edge cases](#transactions--concurrency-edge-cases)
7. [Performance: query budget & N+1](#performance-query-budget--n1)
8. [Security](#security)
9. [Logging](#logging)
10. [Configuration](#configuration)
11. [Testing](#testing)
12. [Tooling: Make, pre-commit, CI, Docker](#tooling-make-pre-commit-ci-docker)
13. [Assumptions, trade-offs & future work](#assumptions-trade-offs--future-work)

---

## Setup and test guide

Follow these steps in order. Total time: about 10 minutes. Every command is run from the repository root.

### Step 0 - What you need installed

| Tool | Why | Check |
|---|---|---|
| **PostgreSQL 14+**, running locally | The project does **not** ship or start a database. | `psql --version` |
| [**uv**](https://docs.astral.sh/uv/getting-started/installation/) | Installs Python 3.13 and the locked dependencies. | `uv --version` |
| **make** | Short commands for everything below (on Windows use WSL). | `make --version` |
| [**Postman**](https://www.postman.com/downloads/) | Calls every endpoint. | open the app |
| Docker (optional) | Only for the Docker option in Step 7. | `docker --version` |

### Step 1 - Get the code

```bash
git clone <repository-url>
cd network-route-optimizer
```

### Step 2 - Create an empty database

PostgreSQL must be running. Create the database the project will use:

```bash
createdb network_route_optimizer
```

If that fails with a role or authentication error, name the PostgreSQL user:

```bash
createdb -U postgres network_route_optimizer
```

Alternatives: in `psql` run `CREATE DATABASE network_route_optimizer;`, or create it in a GUI
(pgAdmin, DBeaver, TablePlus). The database stays empty: the next steps create the tables.

### Step 3 - Configure `.env`

```bash
make env
```

This copies [`.env.example`](.env.example) to `.env` and generates a random `DJANGO_SECRET_KEY`.
Now open `.env` and make `DATABASE_URL` match your PostgreSQL:

```
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/network_route_optimizer
```

Replace `USER` and `PASSWORD` with your PostgreSQL credentials (the example uses `postgres:postgres`).
Leave the other lines as they are. `.env` is git-ignored, so your password is never committed.

### Step 4 - Install and create the tables

```bash
make setup
```

This installs Python 3.13 and the dependencies, installs the git hooks (they only affect your own
commits) and applies the database migrations. Success looks like a list of
`Applying ... OK` lines ending with `routes.0001_initial... OK`.

### Step 5 - Start the API

```bash
make run
```

In a second terminal, check it is up:

```bash
curl localhost:8000/health
# {"status":"ok"}
```

Leave `make run` running while you use Postman.

### Step 6 - Test every endpoint with Postman

**6.1 Import the collection.** In Postman choose **Import** (or `Ctrl/Cmd + O`) and drop in
[`postman/network-route-optimizer.postman_collection.json`](postman/network-route-optimizer.postman_collection.json).
That one file is all you need. `base_url` (`http://localhost:8000/api/v1`) and `health_url`
(`http://localhost:8000/health`) are preset collection variables, so there is no environment to
select and nothing to configure.

**6.2 Quick check: run everything at once.** Click the collection, then **Run** -> **Run Network Route
Optimizer API** (keep the default order). Expected result: **72 passed, 0 failed**. If you see that,
every endpoint works and you can stop here. To check them one at a time, continue.

**6.3 One by one.** Open each request and press **Send**, top to bottom. Folders are ordered so
state flows down (nodes before edges, edges before routes), and each request has built-in tests: look
for green **PASS** in the *Test Results* tab. The demo graph that gets built:

```
A --12.5--> B --10.9--> D     A to D = 23.4 via B
A --5.0---> C --30.0--> D     35.0 via C, so it loses
```

| # | Folder / request | Expect | What it proves |
|---|---|---|---|
| 0 | **0 - Health** > Health | `200 {"status":"ok"}` | Process is up |
| 1 | **1 - Reset demo data** > Reset | `200` | Deletes ALL nodes (edges cascade) so the run starts clean. **Demo database only.** Send it first: it also records the run start time used by the history requests |
| 2 | **2 - Nodes** > Create ServerA, B, C, D | `201 {"id":..,"name":..}` | `POST /nodes` |
| 2 | Create node - duplicate name | `400` "already exists" | Unique names |
| 2 | Create node - name missing | `400` with `details.name` | Validation |
| 2 | Create node - integer name | `400` "Not a valid string." | Names must be strings |
| 2 | List nodes | `200`, bare array of 4 | `GET /nodes` |
| 2 | List nodes - limit=2&offset=1 | `200`, ServerB and ServerC | Pagination |
| 3 | **3 - Edges** > Create A->B, B->D, A->C, C->D | `201`, names (not ids) | `POST /edges` |
| 3 | Create edge - duplicate | `400` "already exists" | Unique edge per direction |
| 3 | Create edge - unknown node | `400` mentions `Ghost` | Both nodes must exist |
| 3 | Create edge - latency <= 0 | `400` with `details.latency` | Positive latency |
| 3 | Create edge - self-loop | `400 {"error": "Source and destination must be different nodes; ..."}` | Self-loops rejected |
| 3 | Create edge - destination missing | `400` with `details.destination` | Validation |
| 3 | List edges | `200`, bare array of 4 | `GET /edges` |
| 4 | **4 - Routes** > Shortest A -> D | `200 {"total_latency":23.4,"path":["ServerA","ServerB","ServerD"]}` | Dijkstra picks the cheaper path |
| 4 | Shortest A -> C | `200 {"total_latency":5,"path":["ServerA","ServerC"]}` | Direct edge |
| 4 | Shortest D -> A (no path) | `404 {"error":"No path exists between ServerD and ServerA"}` | Edges are directed |
| 4 | Shortest - unknown node | `400` mentions `Ghost` | Validation |
| 4 | Shortest - missing field | `400` | Validation |
| 4 | History - all | `200`, 2 records, oldest first | `GET /routes/history` (only successful queries are saved) |
| 4 | History - filter by source + destination | `200`, only A -> D | `source` and `destination` filters |
| 4 | History - limit=1 | `200`, 1 record | `limit` |
| 4 | History - date range | `200`, 2 records | `date_from` and `date_to` |
| 4 | History - inverted date range | `400` | `date_from` after `date_to` is rejected |
| 4 | History - invalid limit | `400` | `limit=abc` is rejected |
| 5 | **5 - Deletes** > Delete edge C -> D | `204` | `DELETE /edges/{id}` |
| 5 | Delete edge again | `404` | Already gone |
| 5 | Delete node ServerB | `204` | `DELETE /nodes/{id}` removes its edges too |
| 5 | Edges after cascade | `200`, only `ServerA->ServerC` | Cascade worked |
| 5 | History still contains the deleted node's queries | `200`, path still includes `ServerB` | History is a snapshot |

Notes: run folders 0 to 5 in order in one session (later requests use ids saved by earlier ones).
The API limits each client to 120 requests per minute and 30 route queries per minute, so if you re-run the whole
collection many times in a row and get `429`, wait a minute.

**6.4 Without the Postman app (optional).** The same collection runs from the terminal with Node.js:

```bash
npx newman run postman/network-route-optimizer.postman_collection.json
```

### Step 7 - Optional extras

**Run the automated tests** (stop `make run` first or use another terminal):

```bash
make test       # whole test-suite, against a real PostgreSQL
make cov        # the same, with the 90 % coverage gate
```

The tests create and drop a temporary `test_...` database, so the PostgreSQL user from Step 3 must
be allowed to create databases (the default `postgres` superuser is).

**Run in Docker instead of `make run`** (the production image; it still uses your local PostgreSQL):

```bash
# in .env, DOCKER_DATABASE_URL must point at the same database through host.docker.internal
make up                       # builds the image, applies migrations, starts the API on :8000
curl localhost:8000/health
make logs                     # optional: tail the logs
make down                     # stop it
```

### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `make setup` fails with `connection refused` | PostgreSQL is not running. Start it, then rerun. |
| `database "network_route_optimizer" does not exist` | Step 2 was skipped, or the name differs from the end of `DATABASE_URL`. |
| `password authentication failed` / `role ... does not exist` | `USER:PASSWORD` in `DATABASE_URL` is not a real PostgreSQL user. Fix `.env`. |
| `DJANGO_SECRET_KEY` / `DATABASE_URL` not set | There is no `.env`. Run `make env`. |
| Postman says *Could not send request* | The API is not running (Step 5) or is on another port. |
| `400 Invalid HTTP_HOST header` | Open the API as `localhost` or `127.0.0.1`, not by another hostname. |
| `429 Too Many Requests` | Rate limit reached. Wait one minute. |
| Port 8000 already in use | Stop the other process, or run `uv run python manage.py runserver 8001` and change `base_url` and `health_url` in the collection's *Variables* tab. |
| `make up` cannot reach the database | `DOCKER_DATABASE_URL` must use host `host.docker.internal`, and PostgreSQL must accept connections from Docker. |

---

## API reference

Base path: `/api/v1` · JSON only · errors share one envelope · **open API: no authentication**
(per the contract).

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| `POST` | `/nodes` | Add node | `201` | `400` missing/blank/duplicate name |
| `GET` | `/nodes` | List nodes - bare array (`?limit=&offset=`) | `200` | `400` bad `limit`/`offset` |
| `DELETE` | `/nodes/{id}` | Delete node (+ its edges) | `204` | `404`, `409` concurrent edge insert (retry) |
| `POST` | `/edges` | Add directed edge | `201` | `400` missing field, latency ≤ 0, duplicate, unknown node, **self-loop** |
| `GET` | `/edges` | List edges - bare array (`?limit=&offset=`) | `200` | `400` bad `limit`/`offset` |
| `DELETE` | `/edges/{id}` | Delete edge | `204` | `404` |
| `POST` | `/routes/shortest` | Lowest-latency path | `200` | `400` invalid/unknown node, `404` no path |
| `GET` | `/routes/history` | Query history, oldest first (as in the contract example) | `200` (bare array) | `400` bad filter |
| `GET` | `/health` | Health check (process is up; does not touch the database) | `200` | - |

### Examples

```bash
H='Content-Type: application/json'
curl -X POST localhost:8000/api/v1/nodes  -H "$H" -d '{"name":"ServerA"}'
# 201 {"id":1,"name":"ServerA"}

curl -X POST localhost:8000/api/v1/edges  -H "$H" \
     -d '{"source":"ServerA","destination":"ServerB","latency":12.5}'
# 201 {"id":1,"source":"ServerA","destination":"ServerB","latency":12.5}

curl -X POST localhost:8000/api/v1/routes/shortest -H "$H" \
     -d '{"source":"ServerA","destination":"ServerD"}'
# 200 {"total_latency":23.4,"path":["ServerA","ServerB","ServerD"]}
# 404 {"error":"No path exists between ServerA and ServerD"}
```

**Lists** (`GET /nodes`, `GET /edges`, `GET /routes/history`) return a **bare array**.
Page with `?limit=` (default 100, max 1000; larger values are clamped) and `?offset=`;
non-numeric, non-positive `limit` or negative `offset` → `400`.

**Self-loop (rejected):**

```bash
curl -X POST localhost:8000/api/v1/edges -H "$H" \
     -d '{"source":"ServerA","destination":"ServerA","latency":10.5}'
# 400 {"error":"Source and destination must be different nodes; an edge cannot connect a node to itself."}
```

**History filters** (all optional, combinable): `source`, `destination`, `date_from`, `date_to`
(inclusive ISO-8601, e.g. `2026-02-20T00:00:00Z`), `limit` and `offset` (as above). Oldest first,
as in the contract's example, so `limit=N` returns the N oldest records in the filter.

**Error envelope** (every non-2xx):

```json
{ "error": "Validation failed.", "details": { "latency": ["Ensure this value is greater than or equal to 0.001."] } }
```

`details` appears for validation errors only. The 404 *no path* body is exactly `{"error": "..."}`
as per the contract.

---

## Architecture

A small, layered, *vertical-slice* design: one app per bounded context (`nodes`, `edges`, `routes`)
plus `common` for cross-cutting infrastructure. Dependencies point **inward**: views → serializers →
repositories → models; reads go through selectors. The one real use-case, the shortest route, has
a service function (`find_shortest_route`) that combines selectors, a path-finding algorithm and one repository write.

```mermaid
flowchart LR
    C[Client] --> MW[Middleware<br/>request-id, access log]
    MW --> V[Views (generic class-based)<br/>throttle, pagination, filters]
    V --> SER[Serializers<br/>validation + create]
    V --> SEL[Selectors<br/>read queries]
    V --> SV[find_shortest_route<br/>shortest route only]
    SV --> SEL
    SER --> REPO[Repositories<br/>writes<br/>constraint -> domain error]
    SV --> REPO
    SV --> PF[dijkstra.shortest_path<br/>pure Python]
    SEL --> ORM[(Django ORM<br/>PostgreSQL + pool)]
    REPO --> ORM
    V -. DomainError .-> EH[Exception handler<br/>uniform error envelope]
```

`POST /routes/shortest` costs 2 SELECTs + 1 INSERT regardless of graph size.

### Project structure

```
config/                     Django project
  settings/{base,development,production,test}.py
  urls.py  wsgi.py
common/                     Cross-cutting infrastructure (no business logic)
  exceptions/               base.py DomainError | handler.py -> one JSON error envelope
  pagination.py             bare-array limit/offset paginator (no COUNT)
  throttling.py middleware.py logging.py   route rate limit, request-id + structured access log
  db.py fields.py models.py views.py   SQLSTATE helpers, StrictCharField, health check, JSON 404/500
apps/
  nodes/                    models selectors repositories serializers views urls exceptions
  edges/                    same shape (depends on nodes)
  routes/                   same shape + services.py (find_shortest_route) + dijkstra.py + filters.py
tests/
  integration/              HTTP contract tests (nodes, edges, routes, platform, throttling)
  performance/              SQL query-budget regression tests
  conftest.py factories.py  shared fixtures and ORM test-data helpers
postman/                    Importable Postman collection
scripts/entrypoint.sh  Dockerfile  docker-compose.yml
Makefile  pyproject.toml  uv.lock  .pre-commit-config.yaml  .github/workflows/ci.yml
```

Unit tests live next to the code they cover (`apps/*/tests`, `common/tests`).
Each domain app follows the same standard DRF layout (`models → serializers → views → urls`) plus
`selectors` (reads) and `repositories` (writes). Creating a node or an edge happens in the
serializer's `create()`; only the routes app has a `services.py`.

---

## Database design

Tables: `nodes_node`, `edges_edge`, `routes_routequery`.

| Concern | Decision |
|---|---|
| Integrity | `UNIQUE(name)`, `UNIQUE(source, destination)`, `CHECK(latency >= 0.001)`, `CHECK(source <> destination)` - enforced by PostgreSQL, so they hold under concurrency and for any writer |
| Latency type | `NUMERIC(10,3)` / `Decimal` (not float): exact sums, e.g. `0.1 + 0.2 = 0.3` |
| Redundant index avoided | `UNIQUE(source, destination)` already serves "outgoing edges of X"; the FK index on `source` is disabled (`db_index=False`) so writes don't maintain a duplicate |
| History is a **snapshot** | `RouteQuery` stores names + path (`jsonb`), **no foreign keys**: history survives node deletion, reads need no joins, writes lock nothing |
| History indexes | `(created_at, id)`, `(source_name, created_at)`, `(destination_name, created_at)` match the filter/sort patterns of `GET /routes/history` |
| Graph is directed | `A→B` and `B→A` are distinct edges |

---

## Design decisions: why this and not that

| Decision | Why | Alternative rejected |
|---|---|---|
| **Writes in the serializer's `create()`** | The standard DRF place for it: `validate()` checks the rules (self-loop, both nodes exist in one query) and `create()` saves through the repository. Only the shortest-route use-case needs a service (`find_shortest_route`) | A service layer for plain create/delete: another layer to explain |
| **Selectors** (reads) vs **repositories** (writes) | CQS: selectors return lazy querysets that DRF filtering/pagination push into SQL; repositories translate DB constraint errors into domain errors | One "manager" doing both; services full of `try/except IntegrityError` |
| **Dijkstra as a pure function** (`dijkstra.py`) | No Django or I/O inside, so it is unit-tested with plain dicts; the service only loads the graph and records the result | Graph math inside the view/model |
| **App per bounded context** (`nodes` → `edges` → `routes`) | One-way dependencies; `routes` reads topology via selectors, so tables can move without touching it | One catch-all app; apps importing each other's models both ways |
| **Top-level `common/`** | Cross-cutting code is not a Django domain app and never imports one | Putting it under `apps/` (blurs the dependency rule) |
| **Domain exceptions → one handler** | Repositories and services stay framework-free; HTTP mapping and envelope are in exactly one place | Raising `APIException` from repositories/services (couples domain to DRF) |
| **DB constraints as source of truth** | Correct under races; no check-then-insert (TOCTOU) | Only `serializer.validate_unique` |
| **Dijkstra in Python, graph loaded in 1 query** | Simple, deterministic, exact (`Decimal`), portable, and costs 3 queries regardless of graph size | PostgreSQL recursive CTE: not expressible in the ORM, awkward for weighted shortest path, harder to test/swap |
| **Native Django pool** (`OPTIONS.pool`) | Built into Django ≥ 5.1; no extra service; one pool per worker process | `CONN_MAX_AGE` (one conn per thread, not a pool) or PgBouncer (extra infra; still an option later) |
| **Generic views** (`ListCreateAPIView` + `DestroyAPIView`) | `GET` and `POST` share one URL, so they need one class; delete is its own URL. Exposes exactly the contract, nothing more (no accidental PUT/PATCH) | `ModelViewSet` + router (also exposes retrieve/update) |
| **django-filter + one array paginator** | Declarative filters and validation → free `400`s; every list endpoint returns a bare array per the contract (`limit`/`offset`, clamped) with no `COUNT(*)` | Hand-parsed `request.query_params` |
| **No authentication** | The contract defines none; adding it would change the interface. No user accounts, cookies or sessions → no CSRF surface, and the Django `auth`/`sessions` apps (and their tables) are not installed | API keys / JWT: out of scope for this contract (see future work) |
| **`uv` + dependency groups** | One lockfile, per-env installs (`prod`/`test`/`dev`), ~10 s resolves, `--frozen` in CI/Docker | pip-tools / requirements files |
| **psycopg 3 (binary)** | Required for Django's native pool; ships wheels, no compiler in the image | psycopg2 (no native pool) |

Separation of concerns: views map HTTP, serializers validate and create, selectors read, repositories persist, algorithms compute.

---

## Transactions & concurrency edge cases

All covered by tests (`apps/nodes/tests/test_repositories.py`, `apps/edges/tests/test_serializers.py`).

| Edge case | Handling |
|---|---|
| Two clients create the **same node** simultaneously | `UNIQUE` constraint arbitrates; loser's `IntegrityError` → `DuplicateNodeError` → `400`. Tested with two real threads - exactly one wins |
| Duplicate **edge** race | Same mechanism (`uniq_edge_source_destination`) |
| Endpoint **deleted between lookup and insert** | The FK violation (PostgreSQL FKs are deferred, checked when the statement's own transaction commits) is raised from the `INSERT` call itself, so it is caught → clean `400`, nothing half-written |
| Node delete races with a new edge | FK violation during delete → `ConflictError` → `409` (client may retry) |
| Node delete | Atomic; edges removed by `ON DELETE CASCADE`; history unaffected |
| Self-loop (`source == destination`, exact/case-sensitive) | Rejected in the serializer's `validate()` **before any query** with `400 {"error": ...}`, and by a `CHECK` constraint as a backstop. Non-positive latency: serializer **and** `CHECK` |
| Error classification | By psycopg SQLSTATE class + constraint name (`common/db.py`), never by parsing message text |
| Transaction scope | No explicit transactions are needed: every write is one statement (atomic in PostgreSQL) and Django wraps cascading deletes in its own transaction. Reads open none |

---

## Performance: query budget & N+1

| Endpoint | Queries | Notes |
|---|---|---|
| `POST /nodes` | 1 INSERT | |
| `POST /edges` | 1 SELECT (both nodes) + 1 INSERT | returned `Edge` already holds both nodes - serialising costs 0 |
| `GET /edges` | 1 joined SELECT | `select_related("source","destination")` - **no N+1** |
| `GET /nodes` | 1 SELECT | `LIMIT/OFFSET`, no `COUNT(*)` |
| `POST /routes/shortest` | 2 SELECT + 1 INSERT | **independent of graph size** (graph loaded with one `values_list` join) |
| `GET /routes/history` | 1 SELECT, no joins | index range scan; `LIMIT` pushed to SQL; no `COUNT(*)` |

These budgets are asserted in `tests/performance/test_query_budgets.py` with `CaptureQueriesContext`,
so any regression (e.g. an accidental lazy FK access) fails CI. The tests count statements rather than
wall-clock time, which keeps them deterministic on shared CI runners.

Dijkstra is `O((V+E) log V)` with a binary heap and early exit on reaching the destination.

---

## Security

* **Secrets from the environment only**; `DJANGO_SECRET_KEY` has no default (crash > insecure run).
  `.env` is git-ignored; `gitleaks` + `detect-private-key` run as hooks.
* **Production fails fast**: refuses to boot without `DJANGO_ALLOWED_HOSTS`, and requests with any other `Host` header get `400` (both tested). `DEBUG=False`, HTTPS redirect, HSTS (1 year, preload).
  `manage.py check --deploy` is clean
  (`DJANGO_SETTINGS_MODULE=config.settings.production DJANGO_ALLOWED_HOSTS=example.com uv run python manage.py check --deploy`).
* **Open by contract**: the exercise specifies no authentication, so none is implemented (and no
  auth/session code or tables exist). Abuse protection therefore relies on throttling, input
  limits and DB timeouts.
* **No CSRF surface by design**: no sessions, no cookies, no ambient credentials
  (`security.W003` is silenced with the rationale documented in settings).
* **Rate limiting**: per-client-IP throttle (`120/min` default, stricter `30/min` for the CPU-heavy
  route endpoint). The health check is exempt.
  Note: counters use Django's cache - use a shared cache (Redis) with multiple workers.
* **Input hardening**: strict serializers, length caps, control characters rejected in names,
  `Decimal` with bounded digits (`NaN`/`Infinity` rejected), JSON-only parser,
  pagination caps (`max_limit`) against resource exhaustion; node names must be real JSON
  strings (a strict field rejects `123` instead of silently coercing it).
* **SQL injection**: ORM only - no raw SQL anywhere.
* **Log injection**: inbound `X-Request-ID` must match `^[A-Za-z0-9._-]{1,64}$` or is replaced;
  query strings/bodies are never logged.
* **Database guard**: `statement_timeout` (5 s) is set on every connection so a runaway query
  cannot pin a pooled connection.
* **Error hygiene**: JSON 404/500 handlers; stack traces are logged, never returned.
* **Container**: multi-stage, non-root numeric UID, no compilers/uv in the runtime image,
  read-only root FS, `cap_drop: ALL`, `no-new-privileges` (compose).
* **Supply chain**: fully locked + hashed (`uv.lock`), `pip-audit` in `make security`/CI,
  `bandit` + ruff `S` rules.

---

## Logging

* Standard library `logging` configured through Django's `LOGGING` dict - no custom framework.
* JSON lines on stdout via `python-json-logger`, at `INFO`.
* **Request correlation**: `RequestContextMiddleware` assigns/propagates `X-Request-ID`, stores it in
  a `ContextVar`, and a `logging.Filter` stamps it on *every* record - ours, Django's and
  third-party - so one id traces a request across layers.
* One structured access line per request (method, path, status, duration). The path is
  percent-encoded, so a newline in a URL cannot forge a log line; `/health` is not logged.
* Repositories log business events (`node created`, `edge deleted`, …) at `INFO`; domain errors at
  `INFO`; unexpected errors at `ERROR` with stack traces via `django.request`. Django's own 4xx
  `WARNING` lines are silenced because the access log already records them (with the request id).

Example (JSON):

```json
{"timestamp": "2026-11-15 05:05:49,133", "level": "INFO", "logger": "common.access",
 "message": "GET /api/v1/routes/history -> 200 (2.04 ms)", "request_id": "13136cbf…",
 "method": "GET", "path": "/api/v1/routes/history", "status": 200, "duration_ms": 2.04}
```

---

## Configuration

Twelve-factor: environment variables (optionally via `.env`, see [`.env.example`](.env.example)).

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` (`manage.py`) / `production` (wsgi) | Environment profile |
| `DJANGO_SECRET_KEY` | *required* | Django secret |
| `DJANGO_ALLOWED_HOSTS` | `localhost,…` (local) / *required* (prod) | Host header allow-list |
| `DATABASE_URL` | *required* | `postgres://user:pass@host:5432/db` |
| `DOCKER_DATABASE_URL` | *required for `make up`* | Same database as seen from the container (`host.docker.internal`); compose passes it on as `DATABASE_URL` |
| `NUM_PROXIES` | `0` | Trusted proxy hops for client-IP detection (`1` behind a load balancer) |
| `SECURE_SSL_REDIRECT` | `true` (prod) | Disable only for plain-HTTP smoke tests |
| `WEB_CONCURRENCY` | `2` (image) | gunicorn workers (read by gunicorn itself) |

---

## Testing

```bash
make test    # everything
make cov     # branch coverage, fails under 90 % (currently ~97 %)

uv run pytest apps common       # unit tests (next to the code)
uv run pytest tests/integration # HTTP contract + platform behaviour
uv run pytest tests/performance # SQL query budgets
```

Tests run against a **real PostgreSQL** (constraints, deferred FKs, the pool and thread races
cannot be faked with SQLite). 96 focused tests - no trivial getter/setter tests:

| Suite | What is verified |
|---|---|
| Unit: algorithm | cheaper multi-hop beats direct, directed graph, unreachable, source = destination, exact `Decimal` sums, deterministic ties, cycles |
| Unit: `find_shortest_route` | unknown nodes rejected, no history for failures, snapshot recorded |
| Unit: database edge cases | concurrent duplicate create (real threads), deferred-FK-at-commit, delete conflict mapping, cascade |
| Unit: settings | production fails fast without allowed hosts and enables hardening |
| Integration: API contract | exact response shapes, every documented `400/404`, parametrised invalid payloads, strict strings, filters/limit/offset/date range, history survives node deletion |
| Integration: platform | pool active, rate limiting (health check exempt), request-id handling, JSON 404/500 |
| Performance | constant SQL statement counts per endpoint (N+1 / `COUNT` regression guards) |

---

## Tooling: Make, pre-commit, CI, Docker

```bash
make help        # list every target
make ci          # exactly what CI runs (lint, types, security, migrations, coverage)
```

**Pre-commit** (`make setup` installs the `pre-commit`, `commit-msg` and `pre-push` hooks):

* *pre-commit*: whitespace/EOF/line-endings, YAML/TOML/JSON/AST validity, merge-conflict & case-conflict,
  large files, debug statements, private keys, **gitleaks**, `uv.lock` in sync, `django-upgrade`,
  **ruff** (lint+format), **mypy** (strict + django/drf stubs), **bandit**, shellcheck, hadolint.
* *commit-msg*: Conventional Commits (`feat:`, `fix:`, `docs:` …).
* *pre-push*: migrations in sync + full test-suite.
* ruff/mypy/bandit run via `uv run`, so hooks use the exact versions pinned in `uv.lock`.

**CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): quality (all hooks + CVE audit) →
tests on PostgreSQL 16 (migration drift, coverage gate) → Docker build.

**Docker**: multi-stage build with `uv sync --frozen --no-dev --group prod`; non-root; healthcheck on
`/health`; `scripts/entrypoint.sh` can apply migrations (`RUN_MIGRATIONS=1`).
For multi-replica deployments run migrations as a separate one-off job instead.

---

## Assumptions, trade-offs & future work

**Decisions** (the exercise left these open; all confirmed):

* Edges are **directed**: `A → B` does not imply `B → A`.
* **Self-loops are rejected** with `400 {"error": "..."}` (exact, case-sensitive comparison, so
  `ServerA → servera` is a valid edge between two different nodes). A *route query* with
  `source == destination` returns a trivial zero-latency path.
* Only **successful** routes are recorded in history; `404`/`400` queries are not.
* History is **oldest-first**, matching the order of the contract's example response (`id` 1 before `id` 2).
  With `limit`, use `date_from` to move to newer records.
* **No authentication** in any environment, per the contract.
* The API is versioned under `/api/v1` (contract paths are unchanged relative to it).
* Node names must be JSON **strings** (numbers are rejected, not coerced), case-sensitive,
  trimmed, ≤ 100 chars, printable.
* Latency unit is milliseconds, up to 3 decimals, max 9,999,999.999.

**Known trade-offs**

* The whole graph is loaded per route query (one query, no N+1). Ideal up to roughly 10⁵ edges.
  Beyond that: cache the adjacency (invalidate on write via `transaction.on_commit`) or precompute.
* Throttle counters use the process-local cache by default; use Redis for multi-worker accuracy.
* The API is unauthenticated by contract. Before exposing it beyond a trusted network, put it behind an
  API gateway / mTLS, or add DRF authentication classes (a settings-only change).

**Future work:** graph cache with version-based invalidation, Redis-backed throttling, OpenTelemetry
tracing/metrics (`/metrics`), history retention/partitioning by month, `k`-shortest / alternative
routes via a second algorithm, bulk import endpoint, optimistic concurrency (`ETag`) if edge
updates are added.
