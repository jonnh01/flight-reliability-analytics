{# Reusable column tests (dbt "generic tests"). A test passes when its query returns 0 rows. #}

{# Every non-null value must lie between min_value and max_value (inclusive). #}
{% test value_between(model, column_name, min_value, max_value) %}
    select {{ column_name }}
    from {{ model }}
    where {{ column_name }} is not null
      and ({{ column_name }} < {{ min_value }} or {{ column_name }} > {{ max_value }})
{% endtest %}

{# The table must contain at least min_rows rows (catches silently empty outputs). #}
{% test has_min_rows(model, min_rows=1) %}
    select 1
    from (select count(*) as n from {{ model }}) as counted
    where n < {{ min_rows }}
{% endtest %}
