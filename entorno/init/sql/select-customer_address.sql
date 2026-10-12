SELECT
    customer_address.ca_address_sk,
    customer_address.ca_address_id,
    customer_address.ca_street_number,
    customer_address.ca_street_name,
    customer_address.ca_street_type,
    customer_address.ca_suite_number,
    CAST(ine_municipios_ordenados.municipio AS varchar(60)) AS ca_city,
    CAST(ine_municipios_ordenados.provincia AS varchar(30)) AS ca_county,
    CAST(ine_municipios_ordenados.provincia_id AS char(2)) AS ca_state,
    customer_address.ca_zip,
    CAST('España' AS varchar(20)) AS ca_country,
    customer_address.ca_gmt_offset,
    customer_address.ca_location_type
FROM tpcds.__TPCDS_SCALE__.customer_address
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados
  ON ine_municipios_ordenados.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(customer_address.ca_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(customer_address.ca_state) AS varchar), '')
      ))),
      ine_municipios_ordenados.total_municipios
  )
