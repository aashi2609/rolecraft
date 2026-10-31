-- Step 7E: EXPLAIN ANALYZE for hot queries
-- Run these BEFORE creating indexes to establish baseline

-- Hot Query 1: Applications by job (job_applications endpoint)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT a.*, j.title, j.company_id, c.email
FROM applications a
JOIN job_postings j ON a.job_id = j.id
LEFT JOIN users c ON a.candidate_id = c.id
WHERE a.job_id = '11111111-1111-1111-1111-111111111111'  -- placeholder UUID
ORDER BY a.applied_at DESC
LIMIT 20;

-- Hot Query 2: Messages by conversation (thread messages)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT m.*, u.email, u.name
FROM messages m
LEFT JOIN users u ON m.sender_id = u.id
WHERE m.conversation_id = '22222222-2222-2222-2222-222222222222'  -- placeholder UUID
ORDER BY m.sent_at DESC
LIMIT 20;

-- Hot Query 3: Notifications for user (notifications list)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT n.*, r.title as resource_title
FROM notifications n
LEFT JOIN job_postings r ON n.resource_id = r.id AND n.resource_type = 'job'
WHERE n.user_id = '33333333-3333-3333-3333-333333333333'  -- placeholder UUID
  AND n.is_read = false
ORDER BY n.created_at DESC
LIMIT 20;

-- Hot Query 4: Applications by candidate (my_applications endpoint)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT a.*, j.title, j.company_id, j.status
FROM applications a
JOIN job_postings j ON a.job_id = j.id
WHERE a.candidate_id = '44444444-4444-4444-4444-444444444444'  -- placeholder UUID
ORDER BY a.applied_at DESC
LIMIT 20;

-- Hot Query 5: Resumes by candidate (candidate's resumes)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT r.*
FROM resumes r
WHERE r.candidate_id = '55555555-5555-5555-5555-555555555555'  -- placeholder UUID
ORDER BY r.updated_at DESC
LIMIT 20;

-- Hot Query 6: Live jobs (browse jobs - high volume)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT j.*
FROM job_postings j
WHERE j.status = 'live'
  AND j.country = 'US'
ORDER BY j.created_at DESC
LIMIT 20;

-- Hot Query 7: Job search by company (company's job postings)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT j.*
FROM job_postings j
WHERE j.company_id = '66666666-6666-6666-6666-666666666666'  -- placeholder UUID
ORDER BY j.created_at DESC
LIMIT 20;

-- Hot Query 8: Unread messages count per conversation
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT conversation_id, COUNT(*) as unread_count
FROM messages
WHERE user_id != sender_id
  AND is_read = false
GROUP BY conversation_id;

-- Hot Query 9: Fitment scores (heavy join, consider vectorized scan)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT fr.*, j.title, c.email
FROM fitment_results fr
JOIN job_postings j ON fr.job_id = j.id
JOIN users c ON fr.candidate_id = c.id
WHERE fr.candidate_id = '77777777-7777-7777-7777-777777777777'
ORDER BY fr.score DESC
LIMIT 20;

-- Hot Query 10: Subscriptions by user (check plan status)
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT s.*, u.email
FROM subscriptions s
JOIN users u ON s.user_id = u.id
WHERE s.user_id = '88888888-8888-8888-8888-888888888888'
ORDER BY s.started_at DESC
LIMIT 1;
