SELECT
    date_add('day', inventory.inv_date_sk - 2415021, DATE '1900-01-01') AS inv_date,
    inventory.inv_item_sk,
    inventory.inv_warehouse_sk,
    inventory.inv_quantity_on_hand
FROM tpcds.__TPCDS_SCALE__.inventory
