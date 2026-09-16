SELECT
    a.web_site_sk,
    a.web_site_id,
    a.web_rec_start_date,
    a.web_rec_end_date,
    a.web_name,
    a.web_open_date_sk,
    a.web_close_date_sk,
    a.web_class,
    a.web_manager,
    a.web_mkt_id,
    a.web_mkt_class,
    a.web_mkt_desc,
    a.web_market_manager,
    a.web_company_id,
    a.web_company_name,
    a.web_street_number,
    a.web_street_name,
    a.web_street_type,
    a.web_suite_number,
    CAST(m.municipio AS varchar(60)) AS web_city,
    CAST(m.provincia AS varchar(30)) AS web_county,
    CAST(m.provincia_id AS char(2)) AS web_state,
    a.web_zip,
    CAST('España' AS varchar(20)) AS web_country,
    a.web_gmt_offset,
    a.web_tax_percentage
FROM tpcds.__TPCDS_SCALE__.web_site AS a
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados AS m
  ON m.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(a.web_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(a.web_state) AS varchar), '')
      ))),
      m.total_municipios
  )
