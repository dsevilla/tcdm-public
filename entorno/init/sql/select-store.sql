SELECT
    store.s_store_sk,
    store.s_store_id,
    vigencia_versiones.vigente_desde AS s_rec_start_date,
    vigencia_versiones.vigente_hasta AS s_rec_end_date,
    date_add('day', store.s_closed_date_sk - 2415021, DATE '1900-01-01') AS s_closed_date,
    store.s_store_name,
    store.s_number_employees,
    store.s_floor_space,
    store.s_hours,
    store.s_manager,
    store.s_market_id,
    store.s_geography_class,
    store.s_market_desc,
    store.s_market_manager,
    store.s_division_id,
    store.s_division_name,
    store.s_company_id,
    store.s_company_name,
    store.s_street_number,
    store.s_street_name,
    store.s_street_type,
    store.s_suite_number,
    CAST(ine_municipios_ordenados.municipio AS varchar(60)) AS s_city,
    CAST(ine_municipios_ordenados.provincia AS varchar(30)) AS s_county,
    CAST(ine_municipios_ordenados.provincia_id AS char(2)) AS s_state,
    store.s_zip,
    CAST('España' AS varchar(20)) AS s_country,
    store.s_gmt_offset,
    store.s_tax_precentage
FROM tpcds.__TPCDS_SCALE__.store
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados
  ON ine_municipios_ordenados.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(store.s_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(store.s_state) AS varchar), '')
      ))),
      ine_municipios_ordenados.total_municipios
  )
JOIN hive.tpcds_bootstrap.vigencia_versiones
  ON vigencia_versiones.dimension = 'store'
 AND vigencia_versiones.clave = store.s_store_sk
