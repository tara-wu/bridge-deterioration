-- Typed, cleaned copy of every raw NBI line. No rows are dropped here;
-- filtering to highway bridges happens in the mart so it stays visible.

with source as (
    select * from {{ source('nbi', 'nbi_records') }}
),

typed as (
    select
        record_year,
        source_file,
        line_number,

        -- identity
        left(trim(state_code), 2)                         as state_fips,
        structure_number                                  as structure_number_raw,
        -- Padding differs between years (leading zeros vs. spaces), so strip both.
        nullif(ltrim(trim(structure_number), '0'), '')    as structure_id,
        trim(record_type)                                 as record_type,
        trim(highway_district)                            as highway_district,
        trim(county_code)                                 as county_code,

        -- location (west longitude is stored unsigned)
        {{ nbi_dms_to_decimal('latitude_raw') }}          as latitude,
        -1 * {{ nbi_dms_to_decimal('longitude_raw') }}    as longitude,

        -- ownership and use
        trim(maintenance_responsibility)                  as maintenance_code,
        trim(owner_code)                                  as owner_code,
        trim(functional_class)                            as functional_class,
        trim(open_posted_closed)                          as open_posted_closed,
        trim(service_on)                                  as service_on,
        trim(service_under)                               as service_under,

        -- structure
        {{ nbi_int('year_built', zero_is_null=true) }}         as year_built,
        {{ nbi_int('year_reconstructed', zero_is_null=true) }} as year_reconstructed,
        trim(material_code)                               as material_code,
        trim(design_code)                                 as design_code,
        {{ nbi_int('main_spans') }}                       as main_spans,
        {{ nbi_int('structure_length_m') }} / 10.0        as structure_length_m,
        {{ nbi_int('deck_width_m') }} / 10.0              as deck_width_m,
        trim(nbis_length) = 'Y'                           as meets_nbis_length,

        -- traffic
        {{ nbi_int('adt') }}                              as adt,
        {{ nbi_int('adt_year', zero_is_null=true) }}      as adt_year,

        -- condition ratings (0-9, null when 'N')
        {{ nbi_rating('deck_cond') }}                     as deck_rating,
        {{ nbi_rating('superstructure_cond') }}           as superstructure_rating,
        {{ nbi_rating('substructure_cond') }}             as substructure_rating,
        {{ nbi_rating('channel_cond') }}                  as channel_rating,
        {{ nbi_rating('culvert_cond') }}                  as culvert_rating,

        -- inspection (item 90 is MMYY)
        try_cast(left(trim(inspection_date), 2) as integer)  as inspection_month,
        try_cast(right(trim(inspection_date), 2) as integer) as inspection_yy,
        {{ nbi_int('inspection_frequency', zero_is_null=true) }} as inspection_frequency_months
    from source
)

select
    * exclude (inspection_yy),
    -- Two-digit year: the latest century that is not after the file year.
    case
        when inspection_yy is null then null
        when 2000 + inspection_yy <= record_year then 2000 + inspection_yy
        else 1900 + inspection_yy
    end as inspection_year
from typed
