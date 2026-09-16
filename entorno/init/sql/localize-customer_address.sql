SELECT
    a.ca_address_sk,
    a.ca_address_id,
    a.ca_street_number,
    a.ca_street_name,
    a.ca_street_type,
    a.ca_suite_number,
    CAST(m.municipio AS char(60)) AS ca_city,
    CAST(m.provincia AS char(30)) AS ca_county,
    CAST(m.provincia_id AS char(2)) AS ca_state,
    a.ca_zip,
    CAST('España' AS char(20)) AS ca_country,
    a.ca_gmt_offset,
    a.ca_location_type
FROM tpcds.__TPCDS_SCALE__.customer_address AS a
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados AS m
  ON m.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(a.ca_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(a.ca_state) AS varchar), '')
      ))),
      m.total_municipios
  )
