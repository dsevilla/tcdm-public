SELECT
    catalog_returns.cr_returned_date_sk,
    catalog_returns.cr_returned_time_sk,
    catalog_returns.cr_item_sk,
    catalog_returns.cr_refunded_customer_sk,
    catalog_returns.cr_refunded_cdemo_sk,
    catalog_returns.cr_refunded_hdemo_sk,
    catalog_returns.cr_refunded_addr_sk,
    catalog_returns.cr_returning_customer_sk,
    catalog_returns.cr_returning_cdemo_sk,
    catalog_returns.cr_returning_hdemo_sk,
    catalog_returns.cr_returning_addr_sk,
    coalesce(vigente.clave, catalog_returns.cr_call_center_sk) AS cr_call_center_sk,
    catalog_returns.cr_catalog_page_sk,
    catalog_returns.cr_ship_mode_sk,
    catalog_returns.cr_warehouse_sk,
    catalog_returns.cr_reason_sk,
    catalog_returns.cr_order_number,
    catalog_returns.cr_return_quantity,
    catalog_returns.cr_return_amount,
    catalog_returns.cr_return_tax,
    catalog_returns.cr_return_amt_inc_tax,
    catalog_returns.cr_fee,
    catalog_returns.cr_return_ship_cost,
    catalog_returns.cr_refunded_cash,
    catalog_returns.cr_reversed_charge,
    catalog_returns.cr_store_credit,
    catalog_returns.cr_net_loss
FROM tpcds.__TPCDS_SCALE__.catalog_returns
LEFT JOIN tpcds.__TPCDS_SCALE__.date_dim
  ON date_dim.d_date_sk = catalog_returns.cr_returned_date_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS original
  ON original.dimension = 'call_center'
 AND original.clave = catalog_returns.cr_call_center_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS vigente
  ON vigente.dimension = 'call_center'
 AND vigente.clave_negocio = original.clave_negocio
 AND date_dim.d_date BETWEEN vigente.vigente_desde
                         AND coalesce(vigente.vigente_hasta, DATE '9999-12-31')
