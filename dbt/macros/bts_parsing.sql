{# Helpers for the quirks of the BTS file. Each one is small on purpose so it is easy to test. #}

{# '15.00' -> 15 ; '' or null -> null #}
{% macro to_int(column) -%}
    round(nullif(trim({{ column }}), '')::numeric)::integer
{%- endmacro %}

{# '1.00' -> true ; '0.00' -> false ; blank -> null #}
{% macro to_bool(column) -%}
    (nullif(trim({{ column }}), '')::numeric = 1)
{%- endmacro %}

{#
  BTS has published FlightDate both as '2026-07-01' and as '7/1/2026 12:00:00 AM'.
  Accept either so a format change upstream does not break the pipeline.
#}
{% macro parse_flight_date(column) -%}
    case
        when {{ column }} ~ '^\d{4}-\d{2}-\d{2}' then left({{ column }}, 10)::date
        when {{ column }} ~ '^\d{1,2}/\d{1,2}/\d{4}' then to_date(split_part({{ column }}, ' ', 1), 'MM/DD/YYYY')
    end
{%- endmacro %}

{#
  Local clock time 'hhmm' -> minutes after midnight.
  '0905' -> 545, '905' -> 545, '2400' -> 1440 (midnight at the END of the day).
  Returns null for blanks and impossible values (minute part > 59).
#}
{% macro hhmm_to_minutes(column) -%}
    case
        when nullif(trim({{ column }}), '') is null then null
        when (round(trim({{ column }})::numeric)::integer % 100) > 59 then null
        else (round(trim({{ column }})::numeric)::integer / 100) * 60
           + (round(trim({{ column }})::numeric)::integer % 100)
    end
{%- endmacro %}
