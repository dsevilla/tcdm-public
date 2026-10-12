SELECT
    store_sales.ss_sold_date_sk,
    store_sales.ss_sold_time_sk,
    store_sales.ss_item_sk,
    store_sales.ss_customer_sk,
    store_sales.ss_cdemo_sk,
    store_sales.ss_hdemo_sk,
    store_sales.ss_addr_sk,
    coalesce(vigente.clave, store_sales.ss_store_sk) AS ss_store_sk,
    store_sales.ss_promo_sk,
    store_sales.ss_ticket_number,
    store_sales.ss_quantity,
    store_sales.ss_wholesale_cost,
    store_sales.ss_list_price,
    store_sales.ss_sales_price,
    store_sales.ss_ext_discount_amt,
    store_sales.ss_ext_sales_price,
    store_sales.ss_ext_wholesale_cost,
    store_sales.ss_ext_list_price,
    store_sales.ss_ext_tax,
    store_sales.ss_coupon_amt,
    store_sales.ss_net_paid,
    store_sales.ss_net_paid_inc_tax,
    store_sales.ss_net_profit
FROM tpcds.__TPCDS_SCALE__.store_sales
LEFT JOIN tpcds.__TPCDS_SCALE__.date_dim
  ON date_dim.d_date_sk = store_sales.ss_sold_date_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS original
  ON original.dimension = 'store'
 AND original.clave = store_sales.ss_store_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS vigente
  ON vigente.dimension = 'store'
 AND vigente.clave_negocio = original.clave_negocio
 AND date_dim.d_date BETWEEN vigente.vigente_desde
                         AND coalesce(vigente.vigente_hasta, DATE '9999-12-31')
