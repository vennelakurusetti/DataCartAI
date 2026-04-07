# 🔍 DataForge AI — Smart E-Commerce Intelligence Platform

> Prompt-driven automated system for generating structured e-commerce datasets using natural language.

## 🚀 Quick Start

```bash
git clone https://github.com/yourname/dataforge-ai.git
cd dataforge-ai
cp .env.example .env
make dev
```

## 🏗️ Architecture

```
User Prompt → NLP Filter Extraction → Multi-Platform Scraper → Data Cleaner → Dataset Output
                                          ↕                          ↕
                                    MLflow Tracking          Airflow Orchestration
```

## 🧩 Tech Stack

| Layer       | Technology                              |
|-------------|------------------------------------------|
| Frontend    | React 18 + TypeScript + Vite + Tailwind  |
| Backend     | FastAPI + Python 3.11                    |
| ML/NLP      | spaCy + HuggingFace Transformers         |
| Scraping    | Playwright + BeautifulSoup4              |
| MLOps       | MLflow + Apache Airflow + DVC            |
| Database    | PostgreSQL + Redis                       |
| Monitoring  | Prometheus + Grafana                     |
| CI/CD       | GitHub Actions + Docker + K8s            |

## 📦 Features
- 🗣️ Natural language prompt → structured dataset
- 🕷️ Multi-platform scraping (Amazon, Flipkart, Meesho)
- 🧠 NLP-based filter extraction
- 📊 Product comparison & recommendations
- 💾 Export to CSV / JSON / Excel
- 📈 Full MLOps pipeline with experiment tracking
- 🔄 Automated retraining & versioning

## 🛠️ Development

```bash
make frontend   # start frontend dev server
make backend    # start backend API server
make airflow    # start Airflow scheduler
make mlflow     # start MLflow UI
make monitor    # start Prometheus + Grafana
```

## 📁 Folder Structure
See FILE_STRUCTURE.md for a detailed breakdown.

## 📄 License
MIT
