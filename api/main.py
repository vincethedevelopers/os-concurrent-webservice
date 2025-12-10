"""
Concurrent Web Service API
Operating Systems Project - COMP6716031

Implements:
- Single-threaded baseline (Version A)
- Multi-threaded with synchronization (Version B)
- Prometheus metrics integration
"""

from fastapi import FastAPI, BackgroundTasks, Query, Response
from fastapi.responses import HTMLResponse
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from contextlib import asynccontextmanager
import asyncio
import threading
import time
import numpy as np
from typing import List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# PROMETHEUS METRICS
# ============================================
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration', ['endpoint'])
ACTIVE_THREADS = Gauge('api_active_threads', 'Number of active threads')
CPU_INTENSIVE_OPS = Counter('api_cpu_operations_total', 'CPU intensive operations completed')
ERRORS = Counter('api_errors_total', 'Total errors', ['type'])

# ============================================
# SYNCHRONIZATION PRIMITIVES
# ============================================
# Mutex untuk shared resource
data_lock = threading.Lock()
shared_counter = 0

# Semaphore untuk limit concurrent operations
max_concurrent_operations = 5
operation_semaphore = threading.Semaphore(max_concurrent_operations)

# ============================================
# SHARED RESOURCE MANAGEMENT
# ============================================
class SharedDataStore:
    """Thread-safe data store dengan mutex"""
    def __init__(self):
        self.data: List[dict] = []
        self.lock = threading.Lock()
        self.operation_count = 0
    
    def add_data(self, item: dict):
        """Thread-safe data addition"""
        with self.lock:  # Mutex lock
            self.data.append(item)
            self.operation_count += 1
            logger.info(f"Data added. Total items: {len(self.data)}")
    
    def get_stats(self):
        """Thread-safe stats retrieval"""
        with self.lock:
            return {
                "total_items": len(self.data),
                "operations": self.operation_count
            }

# Global shared store
shared_store = SharedDataStore()

# ============================================
# CPU INTENSIVE SIMULATION
# ============================================
def cpu_intensive_task(n: int = 1000000) -> float:
    """
    Simulate CPU-intensive work
    Represents database query, complex calculation, etc.
    """
    result = 0
    for i in range(n):
        result += np.sqrt(i) * np.sin(i)
    return result

def io_simulation(duration: float = 0.1):
    """Simulate I/O wait (database, network, etc.)"""
    time.sleep(duration)

# ============================================
# FASTAPI APP
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 API Server Starting...")
    logger.info(f"Max concurrent operations: {max_concurrent_operations}")
    yield
    logger.info("🛑 API Server Shutting Down...")

app = FastAPI(
    title="Concurrent Web Service",
    description="Performance analysis of single vs multi-threaded implementations",
    version="2.0",
    lifespan=lifespan
)

# ============================================
# VERSION A: SINGLE-THREADED BASELINE
# ============================================
@app.get("/api/v1/process-single")
async def process_single(items: int = Query(default=5, ge=1, le=20)):
    """
    VERSION A: Single-threaded sequential processing
    
    Characteristics:
    - Processes requests one by one
    - No parallelism
    - Predictable but slow for multiple operations
    """
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/process-single', method='GET').inc()
    
    results = []
    
    # Sequential processing
    for i in range(items):
        # Simulate work
        cpu_result = cpu_intensive_task(500000)
        io_simulation(0.05)
        
        results.append({
            "task_id": i,
            "result": round(cpu_result, 2),
            "processed_by": "single_thread"
        })
        
        CPU_INTENSIVE_OPS.inc()
    
    duration = time.time() - start_time
    REQUEST_DURATION.labels(endpoint='/process-single').observe(duration)
    
    return {
        "version": "A - Single Threaded",
        "items_processed": items,
        "duration_seconds": round(duration, 3),
        "results": results,
        "concurrency": "none"
    }

# ============================================
# VERSION B: MULTI-THREADED WITH SYNC
# ============================================
def process_task_threaded(task_id: int) -> dict:
    """
    Worker function for thread pool
    Uses semaphore to limit concurrent operations
    """
    with operation_semaphore:  # Semaphore: limit concurrent access
        ACTIVE_THREADS.inc()
        
        try:
            # Simulate work
            cpu_result = cpu_intensive_task(500000)
            io_simulation(0.05)
            
            # Thread-safe counter increment
            global shared_counter
            with data_lock:  # Mutex: protect shared resource
                shared_counter += 1
                current_count = shared_counter
            
            # Add to shared store
            shared_store.add_data({
                "task_id": task_id,
                "thread": threading.current_thread().name,
                "timestamp": time.time()
            })
            
            CPU_INTENSIVE_OPS.inc()
            
            return {
                "task_id": task_id,
                "result": round(cpu_result, 2),
                "processed_by": threading.current_thread().name,
                "counter_value": current_count
            }
        finally:
            ACTIVE_THREADS.dec()

@app.get("/api/v1/process-parallel")
async def process_parallel(items: int = Query(default=5, ge=1, le=20)):
    """
    VERSION B: Multi-threaded parallel processing
    
    Characteristics:
    - Uses ThreadPoolExecutor for parallel execution
    - Semaphore limits max concurrent threads
    - Mutex protects shared counter
    - Better throughput for I/O and CPU bound tasks
    """
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/process-parallel', method='GET').inc()
    
    # Create thread pool
    threads = []
    results = []
    
    # Launch threads
    for i in range(items):
        thread = threading.Thread(
            target=lambda tid: results.append(process_task_threaded(tid)),
            args=(i,)
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    duration = time.time() - start_time
    REQUEST_DURATION.labels(endpoint='/process-parallel').observe(duration)
    
    return {
        "version": "B - Multi-threaded",
        "items_processed": items,
        "duration_seconds": round(duration, 3),
        "results": results,
        "concurrency": "parallel",
        "max_concurrent_threads": max_concurrent_operations,
        "shared_counter": shared_counter,
        "store_stats": shared_store.get_stats()
    }

# ============================================
# ASYNC ENDPOINTS (Non-blocking I/O)
# ============================================
@app.get("/api/v1/process-async")
async def process_async(items: int = Query(default=5, ge=1, le=20)):
    """
    Async/await implementation
    Best for I/O-bound operations
    """
    start_time = time.time()
    REQUEST_COUNT.labels(endpoint='/process-async', method='GET').inc()
    
    async def async_task(task_id: int):
        """Async worker"""
        await asyncio.sleep(0.05)  # Simulate async I/O
        cpu_result = cpu_intensive_task(500000)
        CPU_INTENSIVE_OPS.inc()
        
        return {
            "task_id": task_id,
            "result": round(cpu_result, 2),
            "processed_by": "async_coroutine"
        }
    
    # Run all tasks concurrently
    tasks = [async_task(i) for i in range(items)]
    results = await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    REQUEST_DURATION.labels(endpoint='/process-async').observe(duration)
    
    return {
        "version": "Async/Await",
        "items_processed": items,
        "duration_seconds": round(duration, 3),
        "results": results,
        "concurrency": "async"
    }

# ============================================
# SYSTEM INFO & MONITORING
# ============================================
@app.get("/api/v1/system-info")
async def system_info():
    """Get current system state"""
    import psutil
    import os
    
    return {
        "cpu_count": os.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.Process().memory_percent(),
        "active_threads": threading.active_count(),
        "shared_counter": shared_counter,
        "store_stats": shared_store.get_stats()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    data = generate_latest()
    return Response(
        content=data,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


# ============================================
# UI DASHBOARD
# ============================================
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Apple-inspired minimalist dashboard"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Concurrent Web Service</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif;
                background: #f5f5f7;
                min-height: 100vh;
                color: #1d1d1f;
                line-height: 1.47059;
                font-weight: 400;
                letter-spacing: -.022em;
            }
            
            /* Navigation Bar */
            nav {
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: saturate(180%) blur(20px);
                border-bottom: 1px solid rgba(0, 0, 0, 0.1);
                position: sticky;
                top: 0;
                z-index: 1000;
            }
            
            .nav-content {
                max-width: 1400px;
                margin: 0 auto;
                padding: 16px 40px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .logo {
                font-size: 21px;
                font-weight: 600;
                color: #1d1d1f;
                letter-spacing: -0.5px;
            }
            
            .nav-links {
                display: flex;
                gap: 32px;
                align-items: center;
            }
            
            .nav-links a {
                color: #1d1d1f;
                text-decoration: none;
                font-size: 14px;
                transition: opacity 0.3s;
            }
            
            .nav-links a:hover {
                opacity: 0.6;
            }
            
            /* Hero Section */
            .hero {
                max-width: 1400px;
                margin: 0 auto;
                padding: 80px 40px 60px;
                text-align: center;
            }
            
            h1 {
                font-size: 56px;
                line-height: 1.07143;
                font-weight: 600;
                letter-spacing: -.005em;
                margin-bottom: 12px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            
            .subtitle {
                font-size: 21px;
                line-height: 1.381;
                font-weight: 400;
                color: #6e6e73;
                margin-bottom: 24px;
            }
            
            .description {
                font-size: 17px;
                line-height: 1.47059;
                font-weight: 400;
                color: #86868b;
                max-width: 800px;
                margin: 0 auto 48px;
            }
            
            /* Test Cards Grid */
            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 40px 80px;
            }
            
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 24px;
            }
            
            .card {
                background: #fff;
                border-radius: 18px;
                padding: 40px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }
            
            .card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                opacity: 0;
                transition: opacity 0.3s;
            }
            
            .card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
            }
            
            .card:hover::before {
                opacity: 1;
            }
            
            .card-icon {
                font-size: 48px;
                margin-bottom: 16px;
                display: block;
            }
            
            .card h2 {
                font-size: 28px;
                line-height: 1.14286;
                font-weight: 600;
                letter-spacing: .007em;
                margin-bottom: 8px;
                color: #1d1d1f;
            }
            
            .card-subtitle {
                font-size: 14px;
                color: #86868b;
                margin-bottom: 20px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-weight: 500;
            }
            
            .card-description {
                font-size: 17px;
                line-height: 1.47059;
                color: #6e6e73;
                margin-bottom: 24px;
            }
            
            .specs {
                list-style: none;
                margin-bottom: 32px;
                padding: 0;
            }
            
            .specs li {
                font-size: 14px;
                color: #6e6e73;
                padding: 8px 0;
                border-bottom: 1px solid #f5f5f7;
                display: flex;
                justify-content: space-between;
            }
            
            .specs li:last-child {
                border-bottom: none;
            }
            
            .spec-label {
                color: #86868b;
            }
            
            .spec-value {
                font-weight: 500;
                color: #1d1d1f;
            }
            
            /* Buttons */
            .btn {
                width: 100%;
                padding: 14px 20px;
                border: none;
                border-radius: 980px;
                font-size: 17px;
                font-weight: 400;
                cursor: pointer;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
                text-align: center;
                letter-spacing: -.022em;
            }
            
            .btn-primary {
                background: #0071e3;
                color: #fff;
            }
            
            .btn-primary:hover {
                background: #0077ed;
            }
            
            .btn-secondary {
                background: #1d1d1f;
                color: #fff;
            }
            
            .btn-secondary:hover {
                background: #424245;
            }
            
            /* Results */
            .result-box {
                margin-top: 24px;
                padding: 20px;
                background: #f5f5f7;
                border-radius: 12px;
                display: none;
                animation: fadeIn 0.3s ease-in;
            }
            
            .result-box.show {
                display: block;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .result-title {
                font-size: 19px;
                font-weight: 600;
                margin-bottom: 16px;
                color: #1d1d1f;
            }
            
            .metric-row {
                display: flex;
                justify-content: space-between;
                padding: 12px 0;
                border-bottom: 1px solid #e5e5e7;
            }
            
            .metric-row:last-child {
                border-bottom: none;
            }
            
            .metric-label {
                font-size: 14px;
                color: #86868b;
            }
            
            .metric-value {
                font-size: 17px;
                font-weight: 600;
                color: #0071e3;
            }
            
            /* Loading Spinner */
            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 2px solid #e5e5e7;
                border-top: 2px solid #0071e3;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            /* Footer */
            footer {
                background: #f5f5f7;
                padding: 40px;
                text-align: center;
                border-top: 1px solid #d2d2d7;
                margin-top: 60px;
            }
            
            footer p {
                font-size: 12px;
                color: #86868b;
                margin: 8px 0;
            }
            
            /* Responsive */
            @media (max-width: 768px) {
                h1 {
                    font-size: 40px;
                }
                
                .subtitle {
                    font-size: 19px;
                }
                
                .nav-content {
                    padding: 12px 20px;
                }
                
                .hero {
                    padding: 40px 20px 30px;
                }
                
                .container {
                    padding: 0 20px 40px;
                }
                
                .grid {
                    grid-template-columns: 1fr;
                }
                
                .card {
                    padding: 30px;
                }
                
                .nav-links {
                    gap: 16px;
                }
                
                .nav-links a {
                    font-size: 12px;
                }
            }
        </style>
    </head>
    <body>
        <!-- Navigation -->
        <nav>
            <div class="nav-content">
                <div class="logo">Concurrent OS</div>
                <div class="nav-links">
                    <a href="#tests">Tests</a>
                    <a href="http://localhost:9090" target="_blank">Prometheus</a>
                    <a href="http://localhost:3000" target="_blank">Grafana</a>
                    <a href="/docs" target="_blank">API Docs</a>
                </div>
            </div>
        </nav>
        
        <!-- Hero Section -->
        <section class="hero">
            <h1>Performance at scale.</h1>
            <p class="subtitle">Operating Systems Concurrent Web Service Analysis</p>
            <p class="description">
                Explore the power of parallel processing with real-time monitoring.
                Compare single-threaded, multi-threaded, and async implementations.
            </p>
        </section>
        
        <!-- Test Cards -->
        <div class="container" id="tests">
            <div class="grid">
                <!-- Version A -->
                <div class="card">
                    <span class="card-icon">⚡</span>
                    <div class="card-subtitle">Version A</div>
                    <h2>Single Thread</h2>
                    <p class="card-description">
                        Sequential processing baseline. Simple, predictable, and ideal for understanding core concepts.
                    </p>
                    <ul class="specs">
                        <li>
                            <span class="spec-label">Execution</span>
                            <span class="spec-value">Sequential</span>
                        </li>
                        <li>
                            <span class="spec-label">Concurrency</span>
                            <span class="spec-value">None</span>
                        </li>
                        <li>
                            <span class="spec-label">Complexity</span>
                            <span class="spec-value">Low</span>
                        </li>
                    </ul>
                    <button class="btn btn-primary" onclick="runTest('single', 'result-a')">
                        Run Test
                    </button>
                    <div id="result-a" class="result-box"></div>
                </div>
                
                <!-- Version B -->
                <div class="card">
                    <span class="card-icon">🚀</span>
                    <div class="card-subtitle">Version B</div>
                    <h2>Multi Thread</h2>
                    <p class="card-description">
                        Parallel execution with mutex and semaphore synchronization. Maximum performance for CPU-bound tasks.
                    </p>
                    <ul class="specs">
                        <li>
                            <span class="spec-label">Execution</span>
                            <span class="spec-value">Parallel</span>
                        </li>
                        <li>
                            <span class="spec-label">Sync</span>
                            <span class="spec-value">Mutex + Semaphore</span>
                        </li>
                        <li>
                            <span class="spec-label">Throughput</span>
                            <span class="spec-value">High</span>
                        </li>
                    </ul>
                    <button class="btn btn-primary" onclick="runTest('parallel', 'result-b')">
                        Run Test
                    </button>
                    <div id="result-b" class="result-box"></div>
                </div>
                
                <!-- Async -->
                <div class="card">
                    <span class="card-icon">⚙️</span>
                    <div class="card-subtitle">Async Version</div>
                    <h2>Event Loop</h2>
                    <p class="card-description">
                        Non-blocking I/O with coroutines. Efficient resource usage for network-bound operations.
                    </p>
                    <ul class="specs">
                        <li>
                            <span class="spec-label">Execution</span>
                            <span class="spec-value">Non-blocking</span>
                        </li>
                        <li>
                            <span class="spec-label">Model</span>
                            <span class="spec-value">Event-driven</span>
                        </li>
                        <li>
                            <span class="spec-label">Overhead</span>
                            <span class="spec-value">Minimal</span>
                        </li>
                    </ul>
                    <button class="btn btn-primary" onclick="runTest('async', 'result-async')">
                        Run Test
                    </button>
                    <div id="result-async" class="result-box"></div>
                </div>
                
                <!-- System Info -->
                <div class="card">
                    <span class="card-icon">📊</span>
                    <div class="card-subtitle">Monitoring</div>
                    <h2>System Metrics</h2>
                    <p class="card-description">
                        Real-time system resource monitoring. CPU, memory, threads, and performance counters.
                    </p>
                    <ul class="specs">
                        <li>
                            <span class="spec-label">Metrics</span>
                            <span class="spec-value">Real-time</span>
                        </li>
                        <li>
                            <span class="spec-label">Collection</span>
                            <span class="spec-value">Prometheus</span>
                        </li>
                        <li>
                            <span class="spec-label">Visualization</span>
                            <span class="spec-value">Grafana</span>
                        </li>
                    </ul>
                    <button class="btn btn-secondary" onclick="getSystemInfo()">
                        View Metrics
                    </button>
                    <div id="result-info" class="result-box"></div>
                </div>
            </div>
        </div>
        
        <!-- Footer -->
        <footer>
            <p>Group-6 - Operating Systems</p>
            <p>© 2025-2026 Academic Year</p>
        </footer>
        
        <script>
            async function runTest(type, resultId) {
                const resultBox = document.getElementById(resultId);
                resultBox.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <div class="loading-spinner"></div>
                        <p style="margin-top: 12px; color: #86868b; font-size: 14px;">Processing request...</p>
                    </div>
                `;
                resultBox.classList.add('show');
                
                try {
                    const response = await fetch(`/api/v1/process-${type}?items=10`);
                    const data = await response.json();
                    
                    let html = `<div class="result-title">Test Results</div>`;
                    html += `<div class="metric-row"><span class="metric-label">Version</span><span class="metric-value">${data.version}</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Items Processed</span><span class="metric-value">${data.items_processed}</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Duration</span><span class="metric-value">${data.duration_seconds}s</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Concurrency</span><span class="metric-value">${data.concurrency}</span></div>`;
                    
                    if (data.shared_counter !== undefined) {
                        html += `<div class="metric-row"><span class="metric-label">Shared Counter</span><span class="metric-value">${data.shared_counter}</span></div>`;
                    }
                    
                    resultBox.innerHTML = html;
                } catch (error) {
                    resultBox.innerHTML = `
                        <div class="result-title">Error</div>
                        <p style="color: #ff3b30; font-size: 14px;">${error.message}</p>
                    `;
                }
            }
            
            async function getSystemInfo() {
                const resultBox = document.getElementById('result-info');
                resultBox.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <div class="loading-spinner"></div>
                        <p style="margin-top: 12px; color: #86868b; font-size: 14px;">Fetching metrics...</p>
                    </div>
                `;
                resultBox.classList.add('show');
                
                try {
                    const response = await fetch('/api/v1/system-info');
                    const data = await response.json();
                    
                    let html = `<div class="result-title">System Metrics</div>`;
                    html += `<div class="metric-row"><span class="metric-label">CPU Cores</span><span class="metric-value">${data.cpu_count}</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">CPU Usage</span><span class="metric-value">${data.cpu_percent}%</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Memory Usage</span><span class="metric-value">${data.memory_percent.toFixed(2)}%</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Active Threads</span><span class="metric-value">${data.active_threads}</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Shared Counter</span><span class="metric-value">${data.shared_counter}</span></div>`;
                    html += `<div class="metric-row"><span class="metric-label">Store Items</span><span class="metric-value">${data.store_stats.total_items}</span></div>`;
                    
                    resultBox.innerHTML = html;
                } catch (error) {
                    resultBox.innerHTML = `
                        <div class="result-title">Error</div>
                        <p style="color: #ff3b30; font-size: 14px;">${error.message}</p>
                    `;
                }
            }
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "concurrent-web-api"}