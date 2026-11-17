{# Condition rating (items 58-62): '0'-'9' -> integer; 'N' (not applicable) and blanks -> null. #}
{% macro nbi_rating(column) -%}
    case when regexp_full_match(trim({{ column }}), '[0-9]')
         then cast(trim({{ column }}) as integer) end
{%- endmacro %}

{# Numeric field: blanks and junk -> null. Optionally treat zero as missing. #}
{% macro nbi_int(column, zero_is_null=false) -%}
    {%- if zero_is_null -%}
    nullif(try_cast(trim({{ column }}) as integer), 0)
    {%- else -%}
    try_cast(trim({{ column }}) as integer)
    {%- endif -%}
{%- endmacro %}

{# Items 16/17: DDMMSSss (lat) or DDDMMSSss (long) -> decimal degrees.
   Both share the last six digits MMSSss, so one formula covers both. #}
{% macro nbi_dms_to_decimal(column) -%}
    (
        floor({{ nbi_int(column, zero_is_null=true) }} / 1000000)
        + (floor({{ nbi_int(column, zero_is_null=true) }} / 10000) % 100) / 60.0
        + ({{ nbi_int(column, zero_is_null=true) }} % 10000) / 100.0 / 3600.0
    )
{%- endmacro %}

{# Put models in the schema named in config (staging, marts) rather than
   dbt's default "<target schema>_<custom schema>". #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}
