from mrjob.job import MRJob
from mrjob.protocol import TextProtocol, TextValueProtocol
from typing import Generator

class MRCitingPatents(MRJob):

    # El protocolo de entrada sólo tiene en cuenta el valor (la línea de entrada)
    INPUT_PROTOCOL = TextValueProtocol

    # El protocolo de salida por defecto separa clave y valor por tabulador
    OUTPUT_PROTOCOL = TextProtocol

    def mapper(self, key, value) -> Generator[tuple]:
        # TODO: Completad el mapper
        # ...
        # yield key, value
        ...

    def reducer(self, key, values) -> Generator[tuple]:
        # TODO: Completad el reducer
		# ...
		# yield key, ...
        ...

if __name__ == '__main__':
    MRCitingPatents.run()
