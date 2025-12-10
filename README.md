# OS Concurrent Web Service - Group 6

Project Description
This project is developed for the Operating Systems course (COMP6716031).
It demonstrates and compares different concurrency models in a web service environment:

Version A – Single Thread (sequential processing)

Version B – Multi Thread (mutex and semaphore synchronization)

Async Version – Event Loop (async/await)

The system includes real-time monitoring using Prometheus and Grafana, and performance evaluation using k6 load testing.

System Architecture

API Service

Framework: FastAPI

Port: 8000

Main endpoints:

/api/v1/process-single

/api/v1/process-parallel

/api/v1/process-async

/api/v1/system-info

/metrics (Prometheus endpoint)

/ (UI dashboard)

Monitoring Stack

Prometheus (port 9090)

Grafana (port 3000)

Dashboard: Concurrent API Performance

Load Testing

Tool: k6

Scripts located in load-tests/

Prerequisites

Recommended (Docker):

Docker

Docker Compose

Optional (Manual run):

Python 3.9 or newer

pip

virtualenv (optional)

How to Run (Docker – Recommended)

Clone the repository
git clone https://github.com/USERNAME/os-concurrent-webservice.git

cd os-concurrent-webservice

Build and start all services
docker-compose up --build -d

Check container status
docker-compose ps

Access services

Main API & UI
http://localhost:8000

Prometheus
http://localhost:9090

Grafana
http://localhost:3000

Grafana Login
Username: admin
Password: admin
You may skip or change the password when prompted.

Grafana Dashboard
Dashboard name: Concurrent API Performance
Displays request rate, response time (p50, p95), active threads, CPU operations, and error rate.

Manual API Testing

Single Thread
http://localhost:8000/api/v1/process-single?items=10

Multi Thread
http://localhost:8000/api/v1/process-parallel?items=10

Async / Event Loop
http://localhost:8000/api/v1/process-async?items=10

System Info
http://localhost:8000/api/v1/system-info

Health Check
http://localhost:8000/health

Main UI Dashboard
http://localhost:8000

Monitoring Metrics

Prometheus metrics exposed by the API:

api_requests_total

api_request_duration_seconds_bucket

api_active_threads

api_cpu_operations_total

api_errors_total

Grafana panels filter metrics using endpoint labels such as:

endpoint="/process-single"

endpoint="/process-parallel"

endpoint="/process-async"

Load Testing with k6

Ensure Docker services are running before executing tests.

Basic Load Test
k6 run load-tests/load-test.js

Performance Comparison Test
k6 run load-tests/compare-versions.js

Results are displayed in the terminal.
Some scripts may also generate JSON output files depending on configuration.

Run Without Docker (Optional)

Create and activate virtual environment
python -m venv venv
source venv/bin/activate

Install dependencies
pip install -r requirements.txt

Run the API
uvicorn api.main:app --host 0.0.0.0 --port 8000

Then access the same endpoints via localhost:8000.

Academic Context

Course: Operating Systems – COMP6716031
Institution: Bina Nusantara University
Academic Year: 2025–2026
Group: 6
