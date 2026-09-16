SELECT
    a.cc_call_center_sk,
    a.cc_call_center_id,
    a.cc_rec_start_date,
    a.cc_rec_end_date,
    a.cc_closed_date_sk,
    a.cc_open_date_sk,
    a.cc_name,
    a.cc_class,
    a.cc_employees,
    a.cc_sq_ft,
    a.cc_hours,
    a.cc_manager,
    a.cc_mkt_id,
    a.cc_mkt_class,
    a.cc_mkt_desc,
    a.cc_market_manager,
    a.cc_division,
    a.cc_division_name,
    a.cc_company,
    a.cc_company_name,
    a.cc_street_number,
    a.cc_street_name,
    a.cc_street_type,
    a.cc_suite_number,
    CAST(m.municipio AS varchar(60)) AS cc_city,
    CAST(m.provincia AS varchar(30)) AS cc_county,
    CAST(m.provincia_id AS char(2)) AS cc_state,
    a.cc_zip,
    CAST('España' AS varchar(20)) AS cc_country,
    a.cc_gmt_offset,
    a.cc_tax_percentage
FROM tpcds.__TPCDS_SCALE__.call_center AS a
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados AS m
  ON m.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(a.cc_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(a.cc_state) AS varchar), '')
      ))),
      m.total_municipios
  )
