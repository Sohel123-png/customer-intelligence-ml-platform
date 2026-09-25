# AI-Powered Customer & Product Intelligence Platform

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-A30000)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white)
![Status](https://img.shields.io/badge/status-live%20demo-brightgreen)

**🔗 [Live Demo](https://customer-intelligence-tr7l.onrender.com)** — deployed on Render, no setup required.

> Note: this runs on a free Render instance, so the first request after a period of inactivity can take 30–60 seconds to wake up.

An end-to-end data engineering, machine learning and MLOps project built with Django. It takes data from an external API, cleans and stores it, turns it into ML features, predicts future product stock, checks those predictions against what actually happened, watches for model drift, and shows everything in a multi-page analytics dashboard.

> **Status:** portfolio / learning project. It runs on a free development API (DummyJSON), so the model results demonstrate the pipeline, not real-world forecasting accuracy. See [Limitations](#limitations).

## Project at a glance

| | |
|---|---|
| **Live demo** | [customer-intelligence-tr7l.onrender.com](https://customer-intelligence-tr7l.onrender.com) |
| **Type** | Full-stack data + ML + MLOps system |
| **Problem** | Turn raw product and customer data into predictions, and keep those predictions trustworthy after deployment |
| **Core flow** | Ingest → clean → snapshot → features → predict → evaluate → monitor → detect drift → retrain decision |
| **Stack** | Python, Django, Django REST Framework, scikit-learn, pandas, Celery, Redis, Chart.js |
| **Developed on** | Windows 10/11, Python 3.12+ |

---

## Table of Contents

1. [What this project shows](#what-this-project-shows)
2. [Skills and technologies](#skills-and-technologies)
3. [Features](#features)
4. [Architecture](#architecture)
5. [How the data pipeline works](#how-the-data-pipeline-works)
6. [Key data models](#key-data-models)
7. [Machine learning](#machine-learning)
8. [Monitoring, drift and retraining](#monitoring-drift-and-retraining)
9. [Customer intelligence](#customer-intelligence)
10. [Dashboard](#dashboard)
11. [API reference](#api-reference)
12. [Project structure](#project-structure)
13. [Requirements](#requirements)
14. [Getting started](#getting-started)
15. [Testing the pipeline](#testing-the-pipeline)
16. [Troubleshooting](#troubleshooting)
17. [Deployment (Render)](#deployment-render)
18. [Security considerations](#security-considerations)
19. [Engineering decisions](#engineering-decisions)
20. [Challenges and what I learned](#challenges-and-what-i-learned)
21. [Limitations](#limitations)
22. [Roadmap](#roadmap)
23. [Author](#author)

---

## What this project shows

| Skill area | Where it appears in this project |
|---|---|
| Data engineering | API ingestion, raw vs clean data layers, transformation, data quality tracking, product snapshots, pipeline runs |
| Feature engineering | Lag, change, percentage-change, velocity and rolling-window features built from historical snapshots |
| Machine learning | Temporal train/test split, baseline regression, MAE / RMSE / R² evaluation, model persistence |
| MLOps | Prediction tracking, delayed evaluation, monitoring metrics, drift detection, challenger vs production comparison, model backups |
| Backend engineering | Django, Django REST Framework, ORM models, management commands, service-layer design |
| Background processing | Celery tasks, Celery Beat schedules, Redis broker |
| Analytics and BI | Product and customer analytics APIs, churn analysis, revenue forecast, CSV export for Power BI / Tableau |
| Frontend | Multi-page dashboard with Chart.js visualisations, built with plain HTML, CSS and JavaScript |
| Deployment | Live, publicly deployed on Render with environment-driven config and a health check endpoint |

---

## Skills and technologies

| Category | Skills / tools used |
|---|---|
| Languages | Python, SQL (via Django ORM), JavaScript, HTML, CSS |
| Backend | Django, Django REST Framework, REST API design, management commands, service-layer architecture |
| Data engineering | ETL / ELT-style pipelines, API ingestion, data validation, data quality checks, snapshotting, pipeline run tracking |
| Data analysis | pandas, NumPy, aggregation, time-series feature engineering |
| Machine learning | scikit-learn, regression, classification (churn), temporal validation, MAE / RMSE / R², joblib model persistence |
| MLOps | Model registry, prediction monitoring, drift detection, challenger/champion comparison, model backup and promotion |
| Async and scheduling | Celery, Celery Beat, Redis |
| Databases | SQLite (development), Django ORM; PostgreSQL planned |
| Visualisation and BI | Chart.js, CSV export for Power BI / Tableau / Excel |
| Tools and practice | Git, GitHub, Docker (Redis), virtual environments, environment-based configuration, cloud deployment (Render) |

---

## Features

**Data engineering**
- Ingestion from an external product API
- Raw data stored separately from cleaned data
- Validation and transformation with invalid-record handling
- Duplicate handling and created/updated tracking
- Historical product snapshots on every pipeline run
- Pipeline execution tracking and data-quality checks

**Machine learning**
- Feature engineering from snapshot history
- Temporal train/test split (no future data leaking into training)
- Baseline `LinearRegression` model for next-stock prediction
- Model registry with metadata (features, metrics, training rows, timestamp)

**Prediction and MLOps**
- Every prediction is stored with model name, version and status
- Predictions start as `pending` and become `evaluated` once the real value arrives
- Monitoring of MAE, RMSE and mean error on real predictions
- Drift detection with a minimum-data guard
- Challenger model trained on drift, compared against production, promoted or rejected
- Backup of the production model before any promotion
- Celery + Redis automation

**Analytics**
- Product analytics: price, discount, rating, stock, category insights
- Customer analytics: churn, segments, revenue and revenue forecast, high-risk customers
- AI business analyst endpoint for natural-language questions
- CSV export for BI tools

---

## Architecture

```text
External API (DummyJSON)
        |
        v
   Ingestion service
        |
        v
  RawDataRecord  --->  Transformation & validation
                              |
                              v
                        CleanProduct
                              |
                              v
                       ProductSnapshot   (history, one row per run)
                              |
                              v
                     Feature engineering
                              |
                              v
                       ML model (registry)
                              |
                              v
                      ProductPrediction  (status: pending)
                              |
                  next snapshot arrives with the real stock
                              |
                              v
                    Prediction evaluation  (status: evaluated, error stored)
                              |
                              v
                       Monitoring metrics
                              |
                              v
                        Drift detection
                              |
                   +----------+----------+
                   |                     |
               no drift                drift
                   |                     |
             keep model          train challenger
                                         |
                              compare with production
                                         |
                              +----------+----------+
                              |                     |
                          better -> promote     worse -> reject
                          (after backup)
```

Celery Beat schedules the pipeline and the drift check. Redis is the broker and result backend.

---

## How the data pipeline works

1. **Ingestion.** The service calls the configured product API, records the source and external record id, and saves the response as-is.
2. **Raw storage.** Responses are stored in `RawDataRecord` before any change is made. If something looks wrong later, the original data is still there.
3. **Transformation.** Raw records are validated and converted into clean product records (price, discount, rating, stock, category, brand, source). Invalid records are skipped and counted rather than stopping the whole run.
4. **Snapshots.** Each run writes a `ProductSnapshot` per product: price, discount, rating, stock, capture time and pipeline run. This history is what makes time-based ML possible.
5. **Features.** Snapshots are turned into model inputs (see below).
6. **Prediction and evaluation.** The model predicts the next stock value and stores the prediction. On a later run, the real value is matched to the earlier prediction and the error is calculated.

Run it manually:

```powershell
python manage.py run_pipeline
```

---

## Key data models

| Model | Purpose |
|---|---|
| `RawDataRecord` | Untouched API responses, kept for auditing and debugging |
| `CleanProduct` | Validated, normalised product records |
| `ProductSnapshot` | One observation of a product (price, discount, rating, stock) per pipeline run; the history used for ML |
| `ProductPrediction` | A stored prediction with model name, version and `pending` / `evaluated` status; holds the actual value and error once known |

---

## Machine learning

**Problem:** predict the next observed stock value of a product from its current state and recent history.

**Features** (from `feature_engineering.py` and `snapshot_features.py`):

```text
price, discount_percentage, rating, stock
stock_lag_1, stock_lag_2, price_lag_1, price_lag_2, discount_lag_1
stock_change, price_change, discount_change
stock_change_pct, price_change_pct, discount_change_pct
time_since_previous_minutes, stock_velocity_per_hour
stock_rolling_mean_3, stock_rolling_min_3, stock_rolling_max_3
price_rolling_mean_3, discount_rolling_mean_3
stock_trend
```

**Split:** temporal. The model trains on earlier observations and is tested on later ones.

```text
Past data                          Future data
|--------------------------------| |-----------|
            training                   testing
```

**Model:** scikit-learn `LinearRegression` as a transparent baseline. The point of this project is the pipeline around the model, so the model is intentionally simple and easy to replace.

**Metrics:**
- **MAE**: average absolute error (lower is better)
- **RMSE**: like MAE but punishes large errors more (lower is better)
- **R²**: share of variance the model explains

**Registry:** the trained model and a metadata file (model type, training time, training rows, feature list, MAE, RMSE, R²) are saved under `ml_models/`. These artifacts are generated locally and are not committed to Git.

```powershell
python manage.py train_ml_model
python manage.py model_status
```

---

## Monitoring, drift and retraining

**Prediction lifecycle**

```text
created -> pending -> real value arrives -> evaluated (error stored)
```

**Monitoring** (`/api/ml/monitoring/`) reports total, evaluated and pending predictions, MAE, RMSE, mean error and the most recent predictions.

**Drift detection** (`/api/ml/drift/`)
- Needs at least **10 evaluated predictions**. With fewer, it returns `insufficient_data` instead of guessing.
- Drift is flagged when the MAE of evaluated predictions goes above **5.0**.

**Retraining workflow** (Celery task)

```text
scheduled check -> enough data? -> no: stop
                                -> yes: drift? -> no: stop
                                                -> yes: train challenger
                                                        -> compare with production
                                                        -> promote (after backup) or reject
```

A new model is never promoted automatically just because it exists. It has to beat the production model on the comparison criteria, and the old model is backed up first so there is a basic rollback path.

**Schedules (Celery Beat)**
- Data pipeline: every 5 minutes
- Drift check: every 15 minutes

---

## Customer intelligence

Alongside the product pipeline, the project includes a customer analytics module (`core/`):

- Synthetic customer data generation
- Churn prediction model with per-customer churn probability and top contributing factors
- Customer segmentation
- Monthly revenue history and a 3-month revenue forecast
- High-risk customer list
- CSV export for BI tools (`bi_exports/`)

```powershell
python manage.py generate_data --customers 3000
python manage.py train_models
python manage.py score_customers
python manage.py export_bi_csv
```

---

## Dashboard

A dark, multi-page dashboard served by Django from a single template. Try it live: **[customer-intelligence-tr7l.onrender.com](https://customer-intelligence-tr7l.onrender.com)**. Pages are switched from the sidebar and can be linked directly, for example `/#products`.

| Page | What it shows |
|---|---|
| Overview | Customer KPIs, revenue and forecast, customer segments |
| Customers | Churn by plan and region, high-risk customers |
| Products | Product KPIs, discount and rating analysis, price analysis, business insights, inventory table |
| Stock prediction | Form for the model inputs and the predicted next stock |
| Model monitoring | Prediction counts, MAE, RMSE, mean error, drift status, error trend, recent predictions |
| AI analyst | Ask business questions in plain language |

Charts use Chart.js with gradient fills, depth shadows and staggered animations.

---

## API reference

**Customer analytics**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/analytics/summary/` | Customer KPIs, churn by plan and region |
| GET | `/api/revenue/forecast/?months=3` | Revenue history and forecast |
| GET | `/api/customers/segments/` | Customer segments |
| GET | `/api/customers/high-risk/?limit=15` | Highest churn-risk customers |
| POST | `/api/ask/` | AI business analyst (`{"question": "..."}`) |

**Product analytics**

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/data/analytics/summary/` | Product KPIs |
| GET | `/api/data/analytics/products/` | Product list |
| GET | `/api/data/analytics/price/` | Price statistics |
| GET | `/api/data/analytics/discount/` | Discount analysis |
| GET | `/api/data/analytics/rating/` | Rating analysis |
| GET | `/api/data/analytics/business-insights/` | Category and stock insights |
| GET | `/api/test-products/` | Development product data |

**Machine learning**

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/data/ml/predict/` | Predict next stock from feature values |
| GET | `/api/ml/monitoring/` | Prediction performance metrics |
| GET | `/api/ml/drift/` | Current drift status |

---

## Project structure

```text
churn_platform_django/
├── config/                  # settings, urls, celery, asgi/wsgi
├── core/                    # customer intelligence app
│   ├── models.py, views.py, serializers.py, ml.py, urls.py
│   ├── management/commands/ # generate_data, train_models, score_customers, export_bi_csv
│   └── templates/core/dashboard.html
├── data_engineering/        # product pipeline and MLOps
│   ├── api/ml.py
│   ├── management/commands/ # run_pipeline, train_ml_model, model_status,
│   │                        # sync_source, transform_data, scheduled_pipeline
│   ├── services/            # ingestion, transformation, data_quality,
│   │                        # feature_engineering, snapshot_features, ml_dataset,
│   │                        # ml_model, ml_readiness, model_registry, prediction,
│   │                        # prediction_evaluation, prediction_monitoring,
│   │                        # model_monitoring, analytics, models
│   ├── models.py, tasks.py, urls.py, views.py
├── ml_models/               # generated model artifacts (not committed)
├── bi_exports/              # generated CSV exports
├── manage.py
├── requirements.txt
├── build.sh, render.yaml, Procfile   # deployment
├── .env.example
└── README.md
```

---

## Requirements

### System

| Requirement | Details |
|---|---|
| Operating system | Developed and tested on Windows 10/11. Linux and macOS should work too (there the Celery worker does not need `--pool=solo`) |
| Python | 3.12 or newer |
| Redis | Any recent Redis server, used by Celery as broker and result backend. Easiest via Docker |
| Docker | Optional, only to run Redis in a container |
| Git | To clone the repository |
| Browser | A current Chrome, Edge, Firefox or Safari (the dashboard uses modern CSS such as `color-mix`) |
| Internet access | Needed for the external product API, and for Chart.js and Google Fonts, which the dashboard loads from CDNs |
| Free ports | `8000` (Django) and `6379` (Redis) |

### Python packages

Exact versions are pinned in `requirements.txt`. The main dependencies are:

| Package | Used for |
|---|---|
| Django | Web framework, ORM, management commands |
| djangorestframework | REST API layer |
| celery | Background tasks and scheduled jobs |
| redis | Redis client for Celery |
| pandas, numpy | Data handling and feature engineering |
| scikit-learn | Model training and evaluation |
| joblib | Saving and loading models |

### Configuration

Settings that differ between machines or must stay secret are read from environment variables. Copy `.env.example` to `.env` and fill in your own values (`settings.py` loads it automatically for local runs; real environment variables win). Never commit `.env`.

---

## Getting started

Want to try it without installing anything? Use the **[live demo](https://customer-intelligence-tr7l.onrender.com)** instead. To run it locally:

**Quick start**

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd churn_platform_django
python -m venv .venv
.\.venv\Scripts\activate
pip install uv
uv pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

**Load data and train**

```powershell
# customer module
python manage.py generate_data --customers 3000
python manage.py train_models
python manage.py score_customers

# product pipeline
python manage.py run_pipeline
python manage.py train_ml_model
python manage.py model_status
```

**Start Redis**

```powershell
docker run -d --name churn-redis -p 6379:6379 redis
docker exec churn-redis redis-cli ping     # expect PONG
```

**Start the workers and the server (separate terminals)**

```powershell
celery -A config worker --loglevel=info --pool=solo
celery -A config beat --loglevel=info
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

---

## Testing the pipeline

```powershell
python manage.py check
python manage.py run_pipeline
python manage.py shell
```

```python
from data_engineering.services.models import ProductPrediction

print(ProductPrediction.objects.count())
print(ProductPrediction.objects.filter(status="evaluated").count())
print(ProductPrediction.objects.filter(status="pending").count())
```

Development validation covered: ingestion, transformation, snapshot creation, feature engineering, prediction, prediction persistence, evaluation, MAE/RMSE monitoring, drift detection, Celery task execution, the no-drift retraining decision, model comparison and challenger rejection.

---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| Celery worker crashes or hangs on Windows | Start it with `--pool=solo` |
| Celery cannot connect | Redis is not running. Start the container and check `redis-cli ping` returns `PONG` |
| Drift status shows "Insufficient data" | Fewer than 10 evaluated predictions exist. Run the pipeline a few more times |
| Predict page says the model is missing | Run `python manage.py train_ml_model` first |
| Dashboard charts are empty or fonts look plain | The browser cannot reach the Chart.js / Google Fonts CDNs. Check the internet connection |
| A dashboard section shows an error message | Open the browser console (F12) and check which `/api/...` request failed |
| `ModuleNotFoundError` | The virtual environment is not active, or dependencies were not installed |

---

## Deployment (Render)

The project is live at **[customer-intelligence-tr7l.onrender.com](https://customer-intelligence-tr7l.onrender.com)**, deployed straight from this repo using `render.yaml`, `build.sh` and a `Procfile`.

1. Push the repo to GitHub.
2. Render: **New + > Blueprint**, pick the repo. Render creates the web service and a PostgreSQL database and wires `DATABASE_URL` and a generated `SECRET_KEY` for you.
3. The build runs `build.sh`: install dependencies, `collectstatic`, `migrate`, then `python manage.py bootstrap_demo`.

`bootstrap_demo` exists because trained model files (`*.joblib`) are git-ignored. A fresh deploy would otherwise have empty tables and no models, so the churn, segment, forecast and stock endpoints could not answer. It is idempotent: it generates demo customers, trains the models and scores customers only when they are missing, then warms up the product pipeline and trains the stock model (this last step needs internet access to `dummyjson.com`, and a failure there does not fail the deploy).

Notes:

- Health check: `GET /healthz/`. Missing model files return HTTP `503` with a clear message instead of a `500`.
- On a platform with an ephemeral disk, model files are rebuilt on every deploy. For persistent models, use object storage or a persistent disk.
- Celery beat needs Redis and a separate worker; it is not part of the free single-service setup. Run `python manage.py run_pipeline` manually or as a scheduled job instead.
- Free instances have little RAM (512 MB). The Procfile uses a single gunicorn worker for that reason.
- Other hosts: use `pip install -r requirements.txt` as the build, `bash build.sh` steps as above, and the `Procfile` command to start. Set `SECRET_KEY`, `DEBUG=False`, `DATABASE_URL` and `EXTRA_ALLOWED_HOSTS` / `CSRF_EXTRA_ORIGINS` for your domain.

---

## Security considerations

This is a development project. For a real deployment:

- Keep secrets in environment variables; never hard-code them or commit `.env`.
- Set `DEBUG = False` and restrict `ALLOWED_HOSTS`.
- Add authentication to the API endpoints and restrict CORS.
- Use HTTPS for all external API calls and for the site itself.
- Use a production database (PostgreSQL) with limited access.
- Store model artifacts in managed object storage rather than on local disk.
- Rotate credentials that expire or leak.

---

## Engineering decisions

| Decision | Reason |
|---|---|
| Store raw data before transforming | Keeps the original for debugging and auditing |
| Keep historical snapshots | Time-based ML needs history, not only the current state |
| Temporal split instead of random split | Random splits leak future information into training |
| Evaluate predictions later | A prediction can only be judged once the real value exists |
| Monitor after deployment | Training metrics do not show how the model behaves on new data |
| Minimum data before drift decisions | Drift from one or two points is noise |
| Challenger model instead of direct replacement | A new model can be worse than the current one |
| Back up before promotion | Gives a basic rollback path |
| Simple baseline model | Makes the pipeline easy to verify and the model easy to swap |
| Service-layer structure | Keeps ingestion, features, prediction and monitoring separate and testable |

---

## Challenges and what I learned

- **Time-based data needs different handling.** Splitting by time and building lag and rolling features taught me how easily future information can leak into a model.
- **Evaluation is delayed.** Predictions can only be scored after the next observation, so a `pending` / `evaluated` lifecycle was needed.
- **Little data means no decision.** Early on there were too few evaluated predictions to judge drift, which led to the `insufficient_data` state instead of a made-up answer.
- **Automation needs guard rails.** Retraining runs behind a drift check, a challenger comparison and a backup.
- **Windows and Celery.** Running the worker on Windows needs `--pool=solo`.
- **Source data quality matters more than the model.** The development API does not behave like a real inventory system (see below).

---

## Limitations

- The development source is **DummyJSON**. Its stock values do not follow a realistic, continuously changing inventory pattern, so prediction and monitoring numbers here should **not** be read as production forecasting performance.
- The model is a **linear baseline**, not a tuned production model.
- SQLite and local model files are used for development.
- The drift rule uses a fixed MAE threshold; it does not do statistical drift tests on feature distributions.
- The customer data is synthetic.

The architecture is built so a real, authorized data source can replace the development API without changing the rest of the pipeline.

---

## Roadmap

- **Data:** authenticated production data source, streaming ingestion, data warehouse
- **ML:** tree-based and time-series models, hyperparameter tuning, time-aware cross-validation
- **MLOps:** MLflow, model versioning, object storage for artifacts, feature store, statistical drift tests
- **Infrastructure:** PostgreSQL, Docker Compose, CI/CD, cloud deployment
- **Observability:** Prometheus, Grafana, centralized logging, alerting
- **Security:** API authentication, secrets management, HTTPS, restricted CORS

---

## Author

**Sohel Ali**
Data Science · Machine Learning · Data Engineering · MLOps

- 🔗 Live demo: [customer-intelligence-tr7l.onrender.com](https://customer-intelligence-tr7l.onrender.com)
- GitHub: [Sohel123-png](https://github.com/Sohel123-png)
- LinkedIn: [Sohel Ali](https://www.linkedin.com/in/sohel-ali-6435253a8/)
- Email: sayyedsohelali448@gmail.com

---

## License

Created for educational and portfolio purposes. Add the license you prefer, for example MIT.
