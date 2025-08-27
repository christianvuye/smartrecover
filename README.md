SmartRecover — Recoveries Platform Technical Demonstration
==========================================================

[![CI](https://github.com/christianvuye/smartrecover/actions/workflows/ci.yml/badge.svg)](https://github.com/christianvuye/smartrecover/actions/workflows/ci.yml)

SmartRecover is a technical demonstration of a recoveries platform: maximizing recovery of charged-off loans with priority processing, and minimizing discrepancies between internal and partner systems via event-driven and reconciliation patterns.

Contents
--------
- Overview and Business Value
- Technical Architecture
- Service Definitions
- Service Interaction
- Installation and Setup
- Usage (Management Commands)
- API (Risk Assessment Service)
- Interview Demonstration Points
- Deployment
- Performance Characteristics
- Algorithmic Design
- Scope Boundaries
- Roadmap
- Project Links
- Contributing
- License

Overview and Business Value
---------------------------
SmartRecover helps recovery teams focus on the highest ROI accounts first. By combining a composite risk score with debt amount and using a heap-based priority queue, SmartRecover orchestrates efficient, fault-tolerant batch processing at scale.

- Prioritize accounts by business impact (risk × debt amount)
- Designed to scale to tens of thousands of debtors
- Maintain robust operations with comprehensive error capture

Technical Architecture
----------------------

See also: docs/SystemArchitecture.md

Microservices (current and planned):

```
                           +-----------------------+
                           |  Partner Sync Svc     |
                           |  (planned)            |
                           |  - AWS SQS consumer   |
                           +-----------+-----------+
                                       ^
                                       | SQS (planned)
                                       v
 +----------------------+     +--------+--------+      +------------------+
 |  Risk Assessment Svc |     |  Database (RDS) |      |  Monitoring      |
 |  (this repo)         |<--->|  MySQL (planned)|      |  CloudWatch etc. |
 |  - Heap queue        |     |  SQLite (local) |      +------------------+
 |  - Risk scoring      |     +-----------------+
 |  - Batch processor   |
 +----------------------+
```

- Language: Python 3.13
- Framework: Django 5.2 (+ Django REST Framework)
- Data: SQLite (configured for dev); MySQL (RDS) planned
- Cloud (roadmap): AWS (SQS, EC2/ECS or EKS, RDS)
- Containerization: Docker/Kubernetes (EKS) — roadmap

Service Definitions
-------------------

Risk Assessment Service
- Purpose: Demonstrate efficient algorithmic processing of large datasets using priority queues.
- Core responsibilities: Composite scoring (hash map lookups), heap-based priority processing, batch patterns, error handling and metrics.
- Technical implementation: Django app with `Debtor`/`RiskScore`, `BulkProcessor` using Python `heapq`, management commands, SQLite (dev); MySQL (prod) planned.
- Interview value: Demonstrates efficient data structures, algorithmic complexity, and scalable processing patterns.

Partner Sync Service
- Purpose: Demonstrate distributed systems architecture and data reconciliation patterns between microservices.
- Core responsibilities: Receive messages from Risk Service via SQS, simulate partner sync, discrepancy detection/resolution, exception workflows.
- Technical implementation: Django app with planned `PartnerSyncRecord`/`DiscrepancyRecord`, SQS processing for decoupling, rule-based reconciliation with audit trails.
- Interview value: Shows service communication patterns and financial data reconciliation.

Service Interaction
-------------------

```
Risk Service → SQS Queue → Partner Sync Service
     ↓                            ↓
Priority Processing         Data Reconciliation
     ↓                            ↓
Algorithmic Demo           Integration Patterns
```

Planned Message Flow
1. Risk Service processes debtor records demonstrating heap algorithms.
2. Sends messages to SQS queue: `{debtor_id, debt_amount, risk_score}`.
3. Partner Sync Service receives messages demonstrating event-driven architecture.
4. Shows reconciliation patterns with simulated partner data.

Project Structure
-----------------

```
smartrecover/
  manage.py
  docs/
    SystemArchitecture.md
  risk_service/
    models.py           # Debtor, RiskScore
    risk_scorer.py      # Risk scoring engine
    bulk_processor.py   # Heap-based batch processor
    management/commands/process_debtors.py  # CLI entrypoint
    views.py, serializers.py, urls.py       # DRF API
  partner_sync_service/  # Scaffolding for reconciliation demo (planned features)
    apps.py, models.py, views.py, tests.py
  smartrecover/         # Django project settings/urls
```

Installation and Setup
----------------------

Prerequisites:
- Python 3.13
- pip
- (Optional) MySQL client libraries for mysqlclient when targeting MySQL

1) Clone and create virtual environment
```
cd smartrecover
python3 -m venv .venv
source .venv/bin/activate
python -V  # expect 3.13.x
```

2) Install dependencies
```
pip install -U pip
pip install -r requirements.txt
python -c "import django; print(django.get_version())"  # expect 5.2.x
```

3) Environment configuration
```
cp .env.example .env
# Edit values for local/dev as needed
```

4) Initialize database and run server
```
python manage.py migrate
python manage.py runserver
```

Usage (Management Commands)
---------------------------

Process debtors using the heap-based priority queue (highest priority first):
```
python manage.py process_debtors --batch-size 200 --threshold 750000
```

Dry-run to preview the top 10 accounts without processing:
```
python manage.py process_debtors --dry-run
```

Flags:
- `--batch-size`: Debtors per batch (default 100)
- `--threshold`: High priority threshold (default 500000)
- `--dry-run`: Show top 10 by priority without processing

Generate large-scale test data (balanced/high-risk/low-risk distributions):
```
python manage.py generate_test_debtors --count 50000 --distribution balanced --seed 42
```

Options:
- `--count`: number of debtors to create (default 5000)
- `--clear`: clear existing debtors before generating
- `--distribution`: `balanced` | `high-risk` | `low-risk`
- `--seed`: RNG seed for reproducibility
- `--no-scores`: skip post-generation scoring pass

API (Risk Assessment Service)
----------------------------
Interview Demonstration Points
------------------------------

- Distributed Systems: decoupled services communicating via message queues (planned)
- Algorithms: heap-based priority processing; rule-based reconciliation (planned)
- AWS Integration: SQS messaging; CloudWatch monitoring (planned)
- Operational Engineering: error handling, batch processing, audit trails
- System Design: event-driven architecture; service separation of concerns
- Data Reconciliation: financial patterns for data consistency (planned)


Base path: `/api/risk_service/`

- `GET /debtors/` — list debtors
- `POST /debtors/` — create debtor
- `GET /debtors/<id>/` — retrieve debtor
- `PUT/PATCH /debtors/<id>/` — update debtor (re-scores risk)
- `GET /debtors/<id>/score/` — calculate and return risk score
- `GET /debtors/high-risk/` — list high/critical risk debtors

Performance Characteristics
---------------------------

- Designed to handle 50,000+ debtors efficiently
- O(log n) operations for extraction from the heap
- Batch processing to keep memory bounded
- Measured on Apple M2 (8GB RAM), 30,000 records, batch_size=1000: 505.6 debtors/second (processed 30,000 in 59.339s; 30 batches; 0 errors).
- Throughput varies by hardware and dataset characteristics.

Algorithmic Design
------------------

- Priority = risk_score × debt_amount
- Heap-based priority queue (min-heap with negative priorities)
- Risk scoring uses weighted, normalized factors and O(1) categorical lookups
- Fault tolerance: per-debtor errors recorded without halting the batch

Development Workflow
--------------------

1) Local development only — this is a personal project.
2) There is currently no test suite.
3) Optional: run `python manage.py check` locally.
4) CI runs a minimal Django system check.

Deployment
----------
Scope Boundaries
----------------

In Scope:
- Core algorithmic processing demonstrations
- Basic AWS integration (SQS, CloudWatch) — roadmap
- Automated reconciliation logic patterns — roadmap
- Simple monitoring and alerting — roadmap
- Basic Kubernetes deployment — roadmap

Out of Scope:
- Complex ML algorithms
- Real partner API integrations
- Advanced fraud detection
- Production-scale optimizations


- Local: SQLite and Django dev server
- Staging/Prod (roadmap):
  - AWS RDS (MySQL), EKS or ECS/EC2
  - SQS for inter-service messaging
  - Docker images built via CI/CD, deployed via GitHub Actions → AWS

Roadmap
-------

- Partner Sync Service consuming SQS
- AWS infrastructure-as-code
- Kubernetes manifests/Helm charts
- MySQL migrations and indexing strategy for scale
- Monitoring with CloudWatch dashboards and alerts

Project Links
-------------

- Repository: https://github.com/christianvuye/smartrecover

Contributing
------------

This is a personal project; external contributions are not being accepted.

License
-------

MIT License — see `LICENSE`.


