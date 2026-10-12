SELECT
    web_site.web_site_sk,
    web_site.web_site_id,
    vigencia_versiones.vigente_desde AS web_rec_start_date,
    vigencia_versiones.vigente_hasta AS web_rec_end_date,
    web_site.web_name,
    web_site.web_open_date_sk,
    web_site.web_close_date_sk,
    web_site.web_class,
    web_site.web_manager,
    web_site.web_mkt_id,
    web_site.web_mkt_class,
    web_site.web_mkt_desc,
    web_site.web_market_manager,
    web_site.web_company_id,
    web_site.web_company_name,
    web_site.web_street_number,
    web_site.web_street_name,
    web_site.web_street_type,
    web_site.web_suite_number,
    CAST(ine_municipios_ordenados.municipio AS varchar(60)) AS web_city,
    CAST(ine_municipios_ordenados.provincia AS varchar(30)) AS web_county,
    CAST(ine_municipios_ordenados.provincia_id AS char(2)) AS web_state,
    web_site.web_zip,
    CAST('España' AS varchar(20)) AS web_country,
    web_site.web_gmt_offset,
    web_site.web_tax_percentage
FROM tpcds.__TPCDS_SCALE__.web_site
JOIN hive.tpcds_bootstrap.ine_municipios_ordenados
  ON ine_municipios_ordenados.posicion = 1 + mod(
      crc32(to_utf8(concat(
          coalesce(CAST(trim(web_site.web_city) AS varchar), ''),
          '|',
          coalesce(CAST(trim(web_site.web_state) AS varchar), '')
      ))),
      ine_municipios_ordenados.total_municipios
  )
JOIN hive.tpcds_bootstrap.vigencia_versiones
  ON vigencia_versiones.dimension = 'web_site'
 AND vigencia_versiones.clave = web_site.web_site_sk
