-- Step 7E: Index Audit for Rolecraft
-- Lists all existing indexes and FK columns without indexes

-- 1. All existing indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- 2. Foreign key columns without indexes (critical for query performance)
SELECT 
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name, kcu.column_name;

-- 3. FK columns without indexes (join with pg_indexes to identify)
SELECT 
    tc.table_name,
    kcu.column_name,
    CASE WHEN pi.indexname IS NULL THEN 'NO INDEX' ELSE 'INDEXED' END AS status,
    ccu.table_name AS referenced_table
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu 
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu 
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
LEFT JOIN pg_indexes pi 
    ON pi.tablename = tc.table_name 
    AND pi.schemaname = 'public'
    AND pi.indexdef ILIKE '%' || kcu.column_name || '%'
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
    AND pi.indexname IS NULL
ORDER BY tc.table_name, kcu.column_name;

-- 4. Current table sizes (to determine if concurrent index creation needed)
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
