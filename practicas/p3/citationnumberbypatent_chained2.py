from mrjob.job import MRJob
from mrjob.step import MRStep
from mrjob.protocol import TextProtocol, TextValueProtocol
from typing import Generator

from citingpatents1 import MRCitingPatents

# Esta clase define un protocolo de salida que separa clave y valor por comas
class CSVOutputProtocol(TextProtocol):
    def write(self, key, value) -> bytes:
        return f"{key},{value}".encode('utf-8')

class MRCitationNumberByPatentChained(MRJob):

    # Ficheros a incluir en el trabajo. Tenemos que incluir el fichero
    # que contiene la clase MRCitingPatents
    FILES: list[str] = ['citingpatents1.py']

    # El protocolo de entrada sólo tiene en cuenta el valor (la línea de entrada)
    INPUT_PROTOCOL = TextValueProtocol
    # El protocolo de salida por defecto separa clave y valor por tabulador
    OUTPUT_PROTOCOL = CSVOutputProtocol

    def steps(self) -> list[MRStep]:

        # Trabajo que se utilizará como primer paso
        citingPatentsJob = MRCitingPatents()

        return [
            MRStep(mapper=citingPatentsJob.mapper,
                   reducer=citingPatentsJob.reducer),
            MRStep(mapper=self.mapper)
        ]

    def mapper(self, key, value) -> Generator[tuple]:
        # Line format: cited \t citing1,citing2,citing3,...
        # yield key, ...
        ...

if __name__ == '__main__':
    MRCitationNumberByPatentChained.run()
