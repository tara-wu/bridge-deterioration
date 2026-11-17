-- Warns when the number of bridges changes by more than 10% from one NBI
-- year to the next. Georgia has roughly 15,000 highway bridges and grows
-- slowly, so a jump usually means a broken or truncated file, not real change.
-- This is the first, simplest drift check in the pipeline.
{{ config(severity='warn') }}

with yearly as (
    select record_year, count(*) as bridges
    from {{ ref('bridge_year') }}
    group by record_year
),

compared as (
    select
        record_year,
        bridges,
        lag(bridges) over (order by record_year) as prev_bridges
    from yearly
)

select *
from compared
where prev_bridges is not null
  and abs(bridges - prev_bridges) > 0.10 * prev_bridges
