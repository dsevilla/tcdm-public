from pyspark.sql import SparkSession, DataFrame

def load_data(spark: SparkSession, path_cite: str, path_apat: str) -> tuple[DataFrame, DataFrame]:
    cites: DataFrame = (spark
        .read
        .option("inferSchema", "true")
        .option("header", "true")
        .csv(path_cite))
    cites.printSchema()
    cites.show()
    print(cites.count())

    apat: DataFrame = (spark
        .read
        .option("inferSchema", "true")
        .option("header", "true")
        .csv(path_apat))
    apat.printSchema()
    apat.show()
    print(apat.count())
    return cites, apat
