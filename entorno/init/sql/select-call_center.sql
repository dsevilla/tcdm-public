SELECT
    call_center.cc_call_center_sk,
    call_center.cc_call_center_id,
    vigencia_versiones.vigente_desde AS cc_rec_start_date,
    vigencia_versiones.vigente_hasta AS cc_rec_end_date,
    call_center.cc_closed_date_sk,
    call_center.cc_open_date_sk,
    call_center.cc_name,
    call_center.cc_class,
    call_center.cc_employees,
    call_center.cc_sq_ft,
    call_center.cc_hours,
    call_center.cc_manager,
    call_center.cc_mkt_id,
    call_center.cc_mkt_class,
    call_center.cc_mkt_desc,
    call_center.cc_market_manager,
    call_center.cc_division,
    call_center.cc_division_name,
    call_center.cc_company,
    call_center.cc_company_name,
    call_center.cc_street_number,
    call_center.cc_street_name,
    call_center.cc_street_type,
    call_center.cc_suite_number,
    CAST(ine_municipios_ordenados.municipio AS varchar(60)) AS cc_city,
    CAST(ine_municipios_ordenados.provincia AS varchar(30)) AS cc_county,
    CAST(ine_municipios_ordenados.provincia_id AS char(2)) AS cc_state,
    call_center.cc_zip,
    CAST('España' AS varchar(20)) AS cc_country,
    call_center.cc_gmt_offset,
    call_center.cc_tax_percentage
FROM tpcds.__TPCDS_SCALE__.call_center
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados
  ON ine_municipios_ordenados.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(call_center.cc_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(call_center.cc_state) AS varchar), '')
      ))),
      ine_municipios_ordenados.total_municipios
  )
JOIN hive.tpcds_bootstrap.vigencia_versiones
  ON vigencia_versiones.dimension = 'call_center'
 AND vigencia_versiones.clave = call_center.cc_call_center_sk
