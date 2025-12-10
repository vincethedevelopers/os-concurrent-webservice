/**
 * k6 Load Test Script
 * Tests performance of concurrent web service
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');
const requestCount = new Counter('request_count');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 users
    { duration: '1m', target: 50 },    // Ramp up to 50 users
    { duration: '2m', target: 100 },   // Stay at 100 users
    { duration: '30s', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1000'], // 95% of requests should be below 1s
    'errors': ['rate<0.1'],               // Error rate should be below 10%
  },
};

const BASE_URL = 'http://localhost:8000';

// Test scenarios
export default function() {
  // Test 1: Version A (Single-threaded)
  testEndpoint('/api/v1/process-single?items=5', 'Version A');
  sleep(1);
  
  // Test 2: Version B (Multi-threaded)
  testEndpoint('/api/v1/process-parallel?items=5', 'Version B');
  sleep(1);
  
  // Test 3: Async
  testEndpoint('/api/v1/process-async?items=5', 'Async');
  sleep(1);
  
  // Test 4: System Info
  testEndpoint('/api/v1/system-info', 'System Info');
  sleep(2);
}

function testEndpoint(endpoint, name) {
  const startTime = new Date();
  const response = http.get(`${BASE_URL}${endpoint}`);
  const duration = new Date() - startTime;
  
  // Record metrics
  requestCount.add(1);
  responseTime.add(duration);
  
  // Validate response
  const success = check(response, {
    [`${name} - status is 200`]: (r) => r.status === 200,
    [`${name} - response has body`]: (r) => r.body.length > 0,
    [`${name} - response time < 2s`]: (r) => r.timings.duration < 2000,
  });
  
  if (!success) {
    errorRate.add(1);
    console.error(`${name} failed: ${response.status} - ${response.body}`);
  } else {
    errorRate.add(0);
  }
}

// Summary report
export function handleSummary(data) {
  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
    stdout: textSummary(data),
  };
}

function textSummary(data) {
  const { metrics } = data;
  
  return `
╔══════════════════════════════════════════════════════════╗
║          LOAD TEST SUMMARY - OS PROJECT                  ║
╚══════════════════════════════════════════════════════════╝

📊 REQUEST STATISTICS:
   Total Requests:     ${metrics.http_reqs.values.count}
   Request Rate:       ${metrics.http_reqs.values.rate.toFixed(2)} req/s
   
⏱️  RESPONSE TIME:
   Average:            ${metrics.http_req_duration.values.avg.toFixed(2)} ms
   Median (p50):       ${metrics.http_req_duration.values.med.toFixed(2)} ms
   95th percentile:    ${metrics['http_req_duration{expected_response:true}'].values['p(95)'].toFixed(2)} ms
   99th percentile:    ${metrics['http_req_duration{expected_response:true}'].values['p(99)'].toFixed(2)} ms
   
✅ SUCCESS RATE:
   Successful:         ${((1 - metrics.errors.values.rate) * 100).toFixed(2)}%
   Failed:             ${(metrics.errors.values.rate * 100).toFixed(2)}%
   
🔄 ITERATIONS:
   Total:              ${metrics.iterations.values.count}
   Rate:               ${metrics.iterations.values.rate.toFixed(2)} iter/s

═══════════════════════════════════════════════════════════
`;
}