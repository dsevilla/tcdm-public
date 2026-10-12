SELECT
    warehouse.w_warehouse_sk,
    warehouse.w_warehouse_id,
    warehouse.w_warehouse_name,
    warehouse.w_warehouse_sq_ft,
    warehouse.w_street_number,
    warehouse.w_street_name,
    warehouse.w_street_type,
    warehouse.w_suite_number,
    CAST(ine_municipios_ordenados.municipio AS varchar(60)) AS w_city,
    CAST(ine_municipios_ordenados.provincia AS varchar(30)) AS w_county,
    CAST(ine_municipios_ordenados.provincia_id AS char(2)) AS w_state,
    warehouse.w_zip,
    CAST('España' AS varchar(20)) AS w_country,
    warehouse.w_gmt_offset
FROM tpcds.__TPCDS_SCALE__.warehouse
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados
  ON ine_municipios_ordenados.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(warehouse.w_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(warehouse.w_state) AS varchar), '')
      ))),
      ine_municipios_ordenados.total_municipios
  )
