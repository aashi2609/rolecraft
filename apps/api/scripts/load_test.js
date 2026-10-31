/**
 * Step 7G: Load Test for Rolecraft API
 * 
 * Tests the API under sustained load:
 * - 50 concurrent users for 2 minutes
 * - 90% reads (list jobs, applications, messages)
 * - 10% writes (apply, message, save job)
 * 
 * Run with: k6 run load_test.js
 * Or with CSV output: k6 run --out csv=results.csv load_test.js
 * 
 * Expected baselines (before 7E indexes):
 * - Requests/sec: 100-200
 * - p50 latency: 100-200ms
 * - p95 latency: 500-1000ms (target < 1s)
 * - p99 latency: 1000-2000ms
 * - Error rate: < 1%
 * 
 * After 7E indexes (expected improvement):
 * - Requests/sec: 120-250 (+20-50%)
 * - p95 latency: 300-700ms (20-40% better)
 * - Error rate: < 1%
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const jobListDuration = new Trend('job_list_duration');
const applicationListDuration = new Trend('applications_list_duration');
const threadListDuration = new Trend('threads_list_duration');
const applyjobDuration = new Trend('apply_job_duration');
const sendMessageDuration = new Trend('send_message_duration');

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // Ramp-up to 50 users in 30s
    { duration: '1m30s', target: 50 }, // Stay at 50 users for 1m30s
    { duration: '30s', target: 0 },    // Ramp-down to 0 users in 30s
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],  // p95 < 1s, p99 < 2s
    http_req_failed: ['rate<0.01'],                    // error rate < 1%
    errors: ['rate<0.01'],                             // custom error rate < 1%
  },
  ext: {
    loadimpact: {
      projectID: 0,  // Set to your k6 Cloud project ID if needed
      name: 'Rolecraft Load Test',
    },
  },
};

// Test data (placeholder UUIDs representing seeded data)
const JOB_ID = '11111111-1111-1111-1111-111111111111';
const CONVERSATION_ID = '22222222-2222-2222-2222-222222222222';
const USER_ID = '33333333-3333-3333-3333-333333333333';
const CANDIDATE_ID = '44444444-4444-4444-4444-444444444444';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'test-token';  // Should be valid JWT in production

export default function () {
  // Simulate user's browsing pattern
  if (Math.random() < 0.9) {
    // 90% reads
    browseJobs();
    viewApplications();
    viewMessages();
  } else {
    // 10% writes
    applyToJob();
    sendMessage();
    saveJob();
  }
}

function browseJobs() {
  group('Browse Jobs (Read)', () => {
    let response = http.get(`${BASE_URL}/jobs?page=1&page_size=20`);
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'has items': (r) => r.json().items && r.json().items.length > 0,
      'has pagination': (r) => r.json().total !== undefined,
      'duration < 500ms': (r) => r.timings.duration < 500,
    });
    
    jobListDuration.add(response.timings.duration);
    errorRate.add(!success);
    
    sleep(1);  // Realistic user think time
  });
}

function viewApplications() {
  group('View Applications (Read)', () => {
    let response = http.get(
      `${BASE_URL}/applications/me`,
      {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        },
      }
    );
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'has items': (r) => r.json().items && r.json().items.length >= 0,
      'duration < 500ms': (r) => r.timings.duration < 500,
    });
    
    applicationListDuration.add(response.timings.duration);
    errorRate.add(!success);
    
    sleep(1);
  });
}

function viewMessages() {
  group('View Messages (Read)', () => {
    let response = http.get(
      `${BASE_URL}/threads`,
      {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
        },
      }
    );
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'has items': (r) => r.json().items && r.json().items.length >= 0,
      'duration < 800ms': (r) => r.timings.duration < 800,
    });
    
    threadListDuration.add(response.timings.duration);
    errorRate.add(!success);
    
    sleep(1);
  });
}

function applyToJob() {
  group('Apply to Job (Write)', () => {
    let response = http.post(
      `${BASE_URL}/applications/apply`,
      JSON.stringify({
        job_id: JOB_ID,
      }),
      {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          'Content-Type': 'application/json',
        },
      }
    );
    
    const success = check(response, {
      'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
      'has id': (r) => r.json().id !== undefined,
      'duration < 1000ms': (r) => r.timings.duration < 1000,
    });
    
    applyjobDuration.add(response.timings.duration);
    errorRate.add(!success);
    
    sleep(1);
  });
}

function sendMessage() {
  group('Send Message (Write)', () => {
    let response = http.post(
      `${BASE_URL}/threads/msg`,
      JSON.stringify({
        conversation_id: CONVERSATION_ID,
        body: `Test message from load test - ${new Date().toISOString()}`,
      }),
      {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          'Content-Type': 'application/json',
        },
      }
    );
    
    const success = check(response, {
      'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
      'has id': (r) => r.json().id !== undefined,
      'duration < 800ms': (r) => r.timings.duration < 800,
    });
    
    sendMessageDuration.add(response.timings.duration);
    errorRate.add(!success);
    
    sleep(1);
  });
}

function saveJob() {
  group('Save Job (Write)', () => {
    let response = http.post(
      `${BASE_URL}/saved-jobs`,
      JSON.stringify({
        job_id: JOB_ID,
      }),
      {
        headers: {
          Authorization: `Bearer ${AUTH_TOKEN}`,
          'Content-Type': 'application/json',
        },
      }
    );
    
    const success = check(response, {
      'status is 200 or 201': (r) => r.status === 200 || r.status === 201,
      'duration < 500ms': (r) => r.timings.duration < 500,
    });
    
    errorRate.add(!success);
    
    sleep(1);
  });
}

export function handleSummary(data) {
  /**
   * Generate summary report
   * Run: k6 run --out json=results.json load_test.js
   */
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    'results.json': JSON.stringify(data),
  };
}

/**
 * Custom summary formatter
 */
function textSummary(data, options) {
  const { metrics } = data;
  const lines = [
    '=== Load Test Summary ===',
    `Total Requests: ${metrics.http_reqs.value}`,
    `Failed: ${metrics.http_req_failed.value}`,
    `Error Rate: ${(metrics.http_req_failed.value / metrics.http_reqs.value * 100).toFixed(2)}%`,
    ``,
    'Duration Metrics (ms):',
    `  p50: ${Math.round(metrics.http_req_duration['p(50)'])}`,
    `  p95: ${Math.round(metrics.http_req_duration['p(95)'])}`,
    `  p99: ${Math.round(metrics.http_req_duration['p(99)'])}`,
    `  max: ${Math.round(metrics.http_req_duration['max'])}`,
  ];
  
  return lines.join('\n');
}
