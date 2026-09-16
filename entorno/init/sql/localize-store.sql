SELECT
    a.s_store_sk,
    a.s_store_id,
    a.s_rec_start_date,
    a.s_rec_end_date,
    a.s_closed_date_sk,
    a.s_store_name,
    a.s_number_employees,
    a.s_floor_space,
    a.s_hours,
    a.s_manager,
    a.s_market_id,
    a.s_geography_class,
    a.s_market_desc,
    a.s_market_manager,
    a.s_division_id,
    a.s_division_name,
    a.s_company_id,
    a.s_company_name,
    a.s_street_number,
    a.s_street_name,
    a.s_street_type,
    a.s_suite_number,
    CAST(m.municipio AS varchar(60)) AS s_city,
    CAST(m.provincia AS varchar(30)) AS s_county,
    CAST(m.provincia_id AS char(2)) AS s_state,
    a.s_zip,
    CAST('España' AS varchar(20)) AS s_country,
    a.s_gmt_offset,
    a.s_tax_precentage
FROM tpcds.__TPCDS_SCALE__.store AS a
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados AS m
  ON m.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(a.s_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(a.s_state) AS varchar), '')
      ))),
      m.total_municipios
  )
