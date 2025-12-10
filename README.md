# OS Concurrent Web Service

**Operating Systems (COMP6716031) – Group 6**

## Overview

This project demonstrates and compares different concurrency models in a web service:

* **Single Thread** (sequential)
* **Multi Thread** (mutex & semaphore)
* **Async / Await** (event loop)

The system is monitored using **Prometheus** and **Grafana**, and tested with **k6**.

---

## Tech Stack

* FastAPI (Python)
* Docker & Docker Compose
* Prometheus
* Grafana
* k6 (load testing)

---

## How to Run (Recommended: Docker)

```bash
git clone https://github.com/USERNAME/os-concurrent-webservice.git
cd os-concurrent-webservice
docker-compose up --build -d
```

### Access

* API & UI: [http://localhost:8000](http://localhost:8000)
* Prometheus: [http://localhost:9090](http://localhost:9090)
* Grafana: [http://localhost:3000](http://localhost:3000)

  * Login: `admin / admin`
  * Dashboard: **Concurrent API Performance**

---

## Main Endpoints

```text
/api/v1/process-single
/api/v1/process-parallel
/api/v1/process-async
/api/v1/system-info
/metrics
/
```

Example:

```text
http://localhost:8000/api/v1/process-single?items=10
```

---

## Load Testing (k6)

```bash
k6 run load-tests/load-test.js
k6 run load-tests/compare-versions.js
```

---

## Academic Context

* Course: **Operating Systems (COMP6716031)**
* Institution: **Bina Nusantara University**
* Group: **6**
