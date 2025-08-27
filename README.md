SmartRecover — Fintech Debt Recovery Optimization Platform
==========================================================

SmartRecover is a production-quality debt recovery platform focused on maximizing recovery rates through intelligent prioritization and automated workflows. It demonstrates robust software engineering across algorithms, distributed systems, and cloud infrastructure.

Contents
--------
- Overview and Business Value
- Technical Architecture
- Installation and Setup
- Usage (Management Commands)
- API (Risk Assessment Service)
- Development Workflow
- Deployment
- Performance Characteristics
- Algorithmic Design
- Roadmap
- Contributing
- License

Overview and Business Value
---------------------------
SmartRecover helps recovery teams focus on the highest ROI accounts first. By combining a composite risk score with debt amount and using a heap-based priority queue, SmartRecover orchestrates efficient, fault-tolerant batch processing at scale.

- Prioritize accounts by business impact (risk × debt amount)
- Scale to tens of thousands of debtors
- Maintain robust operations with comprehensive error capture

Technical Architecture
----------------------

Microservices (current and planned):

```
                           +-----------------------+
                           |  Debt Processing Svc  |
                           |  (planned)            |
                           |  - AWS SQS consumer   |
                           +-----------+-----------+
                                       ^
                                       | SQS (AWS)
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
- Data: SQLite (local dev) → MySQL (RDS in prod)
- Cloud: AWS (SQS, EC2/ECS or EKS, RDS)
- Containerization: Docker/Kubernetes (EKS) — roadmap

Project Structure
-----------------

```
smartrecover/
  manage.py
  risk_service/
    models.py           # Debtor, RiskScore
    risk_scorer.py      # Risk scoring engine
    bulk_processor.py   # Heap-based batch processor
    management/commands/process_debtors.py  # CLI entrypoint
    views.py, serializers.py, urls.py       # DRF API
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

API (Risk Assessment Service)
----------------------------

Base path (example): `/risk-service/`

- `GET /debtors/` — list debtors
- `POST /debtors/` — create debtor
- `GET /debtors/<id>/` — retrieve debtor
- `PUT/PATCH /debtors/<id>/` — update debtor (re-scores risk)
- `GET /debtors/<id>/score/` — calculate and return risk score
- `GET /debtors/high-risk/` — list high/critical risk debtors

Performance Characteristics
---------------------------

- Handles 50,000+ debtors efficiently
- O(log n) operations for extraction from the heap
- Batch processing to keep memory bounded
- Throughput ~1000+ debtors/second depending on hardware

Algorithmic Design
------------------

- Priority = risk_score × debt_amount
- Heap-based priority queue (min-heap with negative priorities)
- Risk scoring uses weighted, normalized factors and O(1) categorical lookups
- Fault tolerance: per-debtor errors recorded without halting the batch

Development Workflow
--------------------

1) Create a feature branch
2) Write code and tests
3) Run `python manage.py test`
4) Submit PR and ensure CI is green

Deployment
----------

- Local: SQLite and Django dev server
- Staging/Prod (roadmap):
  - AWS RDS (MySQL), EKS or ECS/EC2
  - SQS for inter-service messaging
  - Docker images built via CI/CD, deployed via GitHub Actions → AWS

Roadmap
-------

- Debt Processing Service (second microservice) consuming SQS
- AWS infrastructure-as-code
- Kubernetes manifests/Helm charts
- MySQL migrations and indexing strategy for scale
- Monitoring with CloudWatch dashboards and alerts

Contributing
------------

Pull requests are welcome. Please include tests and ensure CI passes.

License
-------

MIT License — see `LICENSE`.


