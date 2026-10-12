SELECT
    item.i_item_sk,
    item.i_item_id,
    vigencia_versiones.vigente_desde AS i_rec_start_date,
    vigencia_versiones.vigente_hasta AS i_rec_end_date,
    item.i_item_desc,
    item.i_current_price,
    item.i_wholesale_cost,
    item.i_brand_id,
    item.i_brand,
    item.i_class_id,
    item.i_class,
    item.i_category_id,
    item.i_category,
    item.i_manufact_id,
    item.i_manufact,
    item.i_size,
    item.i_formulation,
    item.i_color,
    item.i_units,
    item.i_container,
    item.i_manager_id,
    item.i_product_name
FROM tpcds.__TPCDS_SCALE__.item
JOIN hive.tpcds_bootstrap.vigencia_versiones
  ON vigencia_versiones.dimension = 'item'
 AND vigencia_versiones.clave = item.i_item_sk
