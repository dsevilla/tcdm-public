from mrjob.job import MRJob
from mrjob.protocol import TextProtocol
from typing import Generator, Any

class MRSortSecundario(MRJob):

    # Se ordenan los valores de salida
    SORT_VALUES: bool = True

    # Se utiliza un particionador que ordena por la clave
    PARTITIONER = 'org.apache.hadoop.mapred.lib.KeyFieldBasedPartitioner'

    # El protocolo de entrada separa las claves por tabulador
    INPUT_PROTOCOL = TextProtocol
    # El protocolo de salida por defecto separa clave y valor por tabulador
    OUTPUT_PROTOCOL = TextProtocol

    def mapper(self, key, value) -> Generator[tuple, Any, None]:
        # Line format: country \t patent,year
        # yield ...,...
        ...

    def reducer(self, key, values) -> Generator[tuple]:
        # key: [country \t year]
        # values: counts
        # yield ...,...
        ...

if __name__ == '__main__':
    MRSortSecundario.run()
