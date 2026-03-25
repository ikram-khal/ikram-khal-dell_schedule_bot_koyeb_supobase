-- ============================================================
-- Запусти этот SQL один раз в Supabase SQL Editor
-- Project: schedule-bot
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    role TEXT,
    teacher_name TEXT,
    group_name TEXT,
    notifications BOOLEAN DEFAULT TRUE,
    state TEXT
);

CREATE TABLE IF NOT EXISTS teachers (
    user_id BIGINT PRIMARY KEY,
    name TEXT,
    "group" TEXT,
    school TEXT
);

CREATE TABLE IF NOT EXISTS students (
    user_id BIGINT PRIMARY KEY,
    name TEXT,
    student_id TEXT,
    "group" TEXT,
    school TEXT
);

CREATE TABLE IF NOT EXISTS schools (
    school TEXT PRIMARY KEY,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS attendance (
    id BIGSERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    name TEXT,
    "group" TEXT,
    school TEXT,
    date TEXT NOT NULL,
    came_time TEXT,
    left_time TEXT,
    status TEXT DEFAULT 'present',
    token TEXT,
    UNIQUE(student_id, date)
);

CREATE TABLE IF NOT EXISTS original_schedule (
    id BIGSERIAL PRIMARY KEY,
    kun TEXT,
    jupliq INTEGER,
    topar TEXT,
    pan TEXT,
    oqitiwshi TEXT,
    kabinet TEXT
);

CREATE TABLE IF NOT EXISTS changes_schedule (
    id BIGSERIAL PRIMARY KEY,
    kun TEXT,
    jupliq INTEGER,
    topar TEXT,
    pan TEXT,
    oqitiwshi TEXT,
    kabinet TEXT
);

CREATE TABLE IF NOT EXISTS exam_schedule (
    id BIGSERIAL PRIMARY KEY,
    kun TEXT,
    waqti TEXT,
    topar TEXT,
    pan TEXT,
    oqitiwshi TEXT,
    kabinet TEXT
);
