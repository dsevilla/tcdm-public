SELECT
    date_add('second', coalesce(web_returns.wr_returned_time_sk, 0), CAST(date_add('day', web_returns.wr_returned_date_sk - 2415021, DATE '1900-01-01') AS timestamp(3))) AS wr_returned_timestamp,
    web_returns.wr_item_sk,
    web_returns.wr_refunded_customer_sk,
    web_returns.wr_refunded_cdemo_sk,
    web_returns.wr_refunded_hdemo_sk,
    web_returns.wr_refunded_addr_sk,
    web_returns.wr_returning_customer_sk,
    web_returns.wr_returning_cdemo_sk,
    web_returns.wr_returning_hdemo_sk,
    web_returns.wr_returning_addr_sk,
    coalesce(vigente.clave, web_returns.wr_web_page_sk) AS wr_web_page_sk,
    web_returns.wr_reason_sk,
    web_returns.wr_order_number,
    web_returns.wr_return_quantity,
    web_returns.wr_return_amt,
    web_returns.wr_return_tax,
    web_returns.wr_return_amt_inc_tax,
    web_returns.wr_fee,
    web_returns.wr_return_ship_cost,
    web_returns.wr_refunded_cash,
    web_returns.wr_reversed_charge,
    web_returns.wr_account_credit,
    web_returns.wr_net_loss
FROM tpcds.__TPCDS_SCALE__.web_returns
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS original
  ON original.dimension = 'web_page'
 AND original.clave = web_returns.wr_web_page_sk
LEFT JOIN hive.tpcds_bootstrap.vigencia_versiones AS vigente
  ON vigente.dimension = 'web_page'
 AND vigente.clave_negocio = original.clave_negocio
 AND date_add('day', web_returns.wr_returned_date_sk - 2415021, DATE '1900-01-01') BETWEEN vigente.vigente_desde
               AND coalesce(vigente.vigente_hasta, DATE '9999-12-31')
