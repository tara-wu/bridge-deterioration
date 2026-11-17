-- One row per highway bridge per NBI year: the table every model in this
-- project starts from.
--
-- Kept: record type 1 (the route carried ON the structure, so each bridge
-- appears once) in the configured state. Structures shorter than NBIS
-- length are kept but flagged, since some years code item 112 inconsistently.

with records as (
    select *
    from {{ ref('stg_nbi__records') }}
    where record_type = '1'
      and state_fips = '{{ var("state_fips") }}'
      and structure_id is not null
),

-- A handful of files repeat a structure within a year; keep the first line
-- and count how many were dropped (see the duplicates test).
deduped as (
    select
        *,
        count(*) over (partition by structure_id, record_year) as lines_in_year
    from records
    qualify row_number() over (
        partition by structure_id, record_year order by line_number
    ) = 1
),

classified as (
    select
        d.*,
        coalesce(d.culvert_rating is not null
                 and d.deck_rating is null
                 and d.superstructure_rating is null, false)     as is_culvert,
        list_min([d.deck_rating, d.superstructure_rating,
                  d.substructure_rating, d.culvert_rating])       as lowest_rating
    from deduped d
),

final as (
    select
        structure_id || '-' || record_year::varchar              as bridge_year_id,
        c.structure_id,
        c.record_year,
        c.county_code,
        c.highway_district,
        c.latitude,
        c.longitude,
        c.owner_code,
        c.maintenance_code,
        c.functional_class,

        c.year_built,
        c.year_reconstructed,
        c.record_year - c.year_built                              as age_years,
        c.record_year - coalesce(c.year_reconstructed, c.year_built)
                                                                  as years_since_work,
        c.material_code,
        m.material_name,
        m.material_group,
        c.design_code,
        c.is_culvert,
        c.main_spans,
        c.structure_length_m,
        c.deck_width_m,
        c.meets_nbis_length,
        c.open_posted_closed,

        c.adt,
        c.adt_year,

        c.deck_rating,
        c.superstructure_rating,
        c.substructure_rating,
        c.culvert_rating,
        c.channel_rating,
        c.lowest_rating,
        case
            when c.lowest_rating is null then 'Unknown'
            when c.lowest_rating >= {{ var('good_min_rating') }} then 'Good'
            when c.lowest_rating <= {{ var('poor_max_rating') }} then 'Poor'
            else 'Fair'
        end                                                       as condition_class,

        c.inspection_year,
        c.inspection_month,
        c.inspection_frequency_months,

        -- Previous NBI year for the same bridge, for transitions and gap checks.
        lag(c.record_year) over w                                 as prev_record_year,
        lag(c.lowest_rating) over w                               as prev_lowest_rating,

        c.lines_in_year,
        c.source_file
    from classified c
    left join {{ ref('material_kinds') }} m on m.material_code = c.material_code
    window w as (partition by c.structure_id order by c.record_year)
)

select
    *,
    case
        when prev_lowest_rating is null then null
        when prev_lowest_rating >= {{ var('good_min_rating') }} then 'Good'
        when prev_lowest_rating <= {{ var('poor_max_rating') }} then 'Poor'
        else 'Fair'
    end as prev_condition_class
from final
