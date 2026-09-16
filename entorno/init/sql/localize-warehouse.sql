SELECT
    a.w_warehouse_sk,
    a.w_warehouse_id,
    a.w_warehouse_name,
    a.w_warehouse_sq_ft,
    a.w_street_number,
    a.w_street_name,
    a.w_street_type,
    a.w_suite_number,
    CAST(m.municipio AS char(60)) AS w_city,
    CAST(m.provincia AS char(30)) AS w_county,
    CAST(m.provincia_id AS char(2)) AS w_state,
    a.w_zip,
    CAST('España' AS char(20)) AS w_country,
    a.w_gmt_offset
FROM tpcds.__TPCDS_SCALE__.warehouse AS a
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados AS m
  ON m.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(a.w_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(a.w_state) AS varchar), '')
      ))),
      m.total_municipios
  )
