{#
  Use the folder's schema name as-is (staging, intermediate, marts, reference)
  instead of dbt's default "<target schema>_<custom schema>" (analytics_marts).
  Cleaner names for the app, Tableau and anyone querying the warehouse.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
