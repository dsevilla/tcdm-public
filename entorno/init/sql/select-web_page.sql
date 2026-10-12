SELECT
    web_page.wp_web_page_sk,
    web_page.wp_web_page_id,
    vigencia_versiones.vigente_desde AS wp_rec_start_date,
    vigencia_versiones.vigente_hasta AS wp_rec_end_date,
    date_add('day', web_page.wp_creation_date_sk - 2415021, DATE '1900-01-01') AS wp_creation_date,
    date_add('day', web_page.wp_access_date_sk - 2415021, DATE '1900-01-01') AS wp_access_date,
    web_page.wp_autogen_flag,
    web_page.wp_customer_sk,
    web_page.wp_url,
    web_page.wp_type,
    web_page.wp_char_count,
    web_page.wp_link_count,
    web_page.wp_image_count,
    web_page.wp_max_ad_count
FROM tpcds.__TPCDS_SCALE__.web_page
JOIN hive.tpcds_bootstrap.vigencia_versiones
  ON vigencia_versiones.dimension = 'web_page'
 AND vigencia_versiones.clave = web_page.wp_web_page_sk
