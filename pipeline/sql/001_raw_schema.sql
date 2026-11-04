-- Raw layer: flights exactly as BTS published them (all text), plus load bookkeeping.
-- Safe to run repeatedly.

create schema if not exists raw;

create table if not exists raw.bts_flights (
    year                text,
    month               text,
    flight_date         text,
    reporting_airline   text,
    tail_number         text,
    flight_number       text,
    origin              text,
    origin_city_name    text,
    origin_state        text,
    dest                text,
    dest_city_name      text,
    dest_state          text,
    crs_dep_time        text,
    dep_time            text,
    dep_delay           text,
    crs_arr_time        text,
    arr_time            text,
    arr_delay           text,
    arr_del15           text,
    cancelled           text,
    cancellation_code   text,
    diverted            text,
    crs_elapsed_time    text,
    actual_elapsed_time text,
    distance            text,
    carrier_delay       text,
    weather_delay       text,
    nas_delay           text,
    security_delay      text,
    late_aircraft_delay text,
    -- source metadata, filled by the loader
    _year_month         integer     not null,
    _source_file        text        not null,
    _source_sha256      text        not null,
    _loaded_at          timestamptz not null
);

-- Reloading a month = delete its rows, then COPY. This index makes the delete fast.
create index if not exists ix_raw_bts_flights_year_month on raw.bts_flights (_year_month);

-- One row per month currently in raw.bts_flights. The loader's source of truth for
-- "is this month already loaded, and is it the same file?"
create table if not exists raw.load_log (
    year_month     integer primary key,
    source_file    text        not null,
    source_url     text,
    archive_uri    text,
    source_sha256  text        not null,
    row_count      integer     not null,
    loaded_at      timestamptz not null,
    run_id         text        not null
);

-- One row per pipeline run: the monitoring history.
create table if not exists raw.pipeline_runs (
    run_id           text primary key,
    started_at       timestamptz not null,
    finished_at      timestamptz,
    status           text not null check (status in ('running', 'success', 'no_new_data', 'failed')),
    months_requested text,
    months_loaded    text,
    months_skipped   text,
    rows_loaded      bigint default 0,
    error_message    text
);
