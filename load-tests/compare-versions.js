/**
 * Comparison Test: Version A vs Version B vs Async
 * Measures throughput and latency differences
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

// Separate metrics for each version
const versionA_time = new Trend('version_a_response_time');
const versionB_time = new Trend('version_b_response_time');
const versionAsync_time = new Trend('version_async_response_time');

export const options = {
  scenarios: {
    version_a_test: {
      executor: 'constant-vus',
      vus: 20,
      duration: '1m',
      exec: 'testVersionA',
    },
    version_b_test: {
      executor: 'constant-vus',
      vus: 20,
      duration: '1m',
      exec: 'testVersionB',
      startTime: '1m',
    },
    async_test: {
      executor: 'constant-vus',
      vus: 20,
      duration: '1m',
      exec: 'testAsync',
      startTime: '2m',
    },
  },
};

const BASE_URL = 'http://localhost:8000';

export function testVersionA() {
  const response = http.get(`${BASE_URL}/api/v1/process-single?items=10`);
  
  check(response, {
    'Version A - Success': (r) => r.status === 200,
  });
  
  versionA_time.add(response.timings.duration);
  sleep(0.5);
}

export function testVersionB() {
  const response = http.get(`${BASE_URL}/api/v1/process-parallel?items=10`);
  
  check(response, {
    'Version B - Success': (r) => r.status === 200,
  });
  
  versionB_time.add(response.timings.duration);
  sleep(0.5);
}

export function testAsync() {
  const response = http.get(`${BASE_URL}/api/v1/process-async?items=10`);
  
  check(response, {
    'Async - Success': (r) => r.status === 200,
  });
  
  versionAsync_time.add(response.timings.duration);
  sleep(0.5);
}

export function handleSummary(data) {
  const versionA = data.metrics.version_a_response_time.values;
  const versionB = data.metrics.version_b_response_time.values;
  const versionAsync = data.metrics.version_async_response_time.values;
  
  console.log(`
╔════════════════════════════════════════════════════════════════════╗
║                   PERFORMANCE COMPARISON                           ║
╚════════════════════════════════════════════════════════════════════╝

┌─ VERSION A (Single-threaded) ─────────────────────────────────────┐
│ Average Response Time:     ${versionA.avg.toFixed(2)} ms
│ Median (p50):              ${versionA.med.toFixed(2)} ms
│ 95th Percentile:           ${versionA['p(95)'].toFixed(2)} ms
│ Min:                       ${versionA.min.toFixed(2)} ms
│ Max:                       ${versionA.max.toFixed(2)} ms
└───────────────────────────────────────────────────────────────────┘

┌─ VERSION B (Multi-threaded) ──────────────────────────────────────┐
│ Average Response Time:     ${versionB.avg.toFixed(2)} ms
│ Median (p50):              ${versionB.med.toFixed(2)} ms
│ 95th Percentile:           ${versionB['p(95)'].toFixed(2)} ms
│ Min:                       ${versionB.min.toFixed(2)} ms
│ Max:                       ${versionB.max.toFixed(2)} ms
│ 
│ 🚀 SPEEDUP vs Version A:   ${(versionA.avg / versionB.avg).toFixed(2)}x
└───────────────────────────────────────────────────────────────────┘

┌─ ASYNC (Event Loop) ──────────────────────────────────────────────┐
│ Average Response Time:     ${versionAsync.avg.toFixed(2)} ms
│ Median (p50):              ${versionAsync.med.toFixed(2)} ms
│ 95th Percentile:           ${versionAsync['p(95)'].toFixed(2)} ms
│ Min:                       ${versionAsync.min.toFixed(2)} ms
│ Max:                       ${versionAsync.max.toFixed(2)} ms
│ 
│ 🚀 SPEEDUP vs Version A:   ${(versionA.avg / versionAsync.avg).toFixed(2)}x
└───────────────────────────────────────────────────────────────────┘

📊 KEY INSIGHTS:
   • Version B is ${((1 - versionB.avg / versionA.avg) * 100).toFixed(1)}% faster than Version A
   • Async is ${((1 - versionAsync.avg / versionA.avg) * 100).toFixed(1)}% faster than Version A
   • Best performer: ${versionB.avg < versionAsync.avg ? 'Version B (Multi-threaded)' : 'Async (Event Loop)'}

═══════════════════════════════════════════════════════════════════
  `);
  
  return {
    'comparison-results.json': JSON.stringify({
      version_a: versionA,
      version_b: versionB,
      version_async: versionAsync,
      speedup_b: (versionA.avg / versionB.avg).toFixed(2),
      speedup_async: (versionA.avg / versionAsync.avg).toFixed(2),
    }, null, 2),
  };
}