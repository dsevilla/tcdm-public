SELECT
    store_returns.sr_returned_date_sk,
    store_returns.sr_return_time_sk,
    store_returns.sr_item_sk,
    store_returns.sr_customer_sk,
    store_returns.sr_cdemo_sk,
    store_returns.sr_hdemo_sk,
    store_returns.sr_addr_sk,
    coalesce(vigente.clave, store_returns.sr_store_sk) AS sr_store_sk,
    store_returns.sr_reason_sk,
    store_returns.sr_ticket_number,
    store_returns.sr_return_quantity,
    store_returns.sr_return_amt,
    store_returns.sr_return_tax,
    store_returns.sr_return_amt_inc_tax,
    store_returns.sr_fee,
    store_returns.sr_return_ship_cost,
    store_returns.sr_refunded_cash,
    store_returns.sr_reversed_charge,
    store_returns.sr_store_credit,
    store_returns.sr_net_loss
FROM tpcds.__TPCDS_SCALE__.store_returns
LEFT JOIN tpcds.__TPCDS_SCALE__.date_dim
  ON date_dim.d_date_sk = store_returns.sr_returned_date_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS original
  ON original.dimension = 'store'
 AND original.clave = store_returns.sr_store_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS vigente
  ON vigente.dimension = 'store'
 AND vigente.clave_negocio = original.clave_negocio
 AND date_dim.d_date BETWEEN vigente.vigente_desde
                         AND coalesce(vigente.vigente_hasta, DATE '9999-12-31')
