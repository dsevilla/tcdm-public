from pyspark.sql import SparkSession

def get_spark_session(appname: str) -> SparkSession:
    spark: SparkSession = SparkSession\
        .builder\
        .appName(appname)\
        .getOrCreate()

    # Cambio la verbosidad para reducir el número de
    # mensajes por pantalla
    spark.sparkContext.setLogLevel("FATAL")

    return spark
