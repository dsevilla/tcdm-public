from mrjob.job import MRJob
from mrjob.protocol import TextProtocol, TextValueProtocol

class MRCountryPatents(MRJob):

    # El fichero country_codes.txt se incluirá en el trabajo
    FILES: list[str] = ['country_codes.txt']

    # El protocolo de entrada sólo tiene en cuenta el valor (la línea de entrada)
    INPUT_PROTOCOL = TextValueProtocol
    # El protocolo de salida por defecto separa clave y valor por tabulador
    OUTPUT_PROTOCOL = TextProtocol

    country_map: dict[str,str] = {}

    def mapper(self, key, value):
        # Line format: "PATENT","GYEAR","GDATE","APPYEAR","COUNTRY","POSTATE","ASSIGNEE","ASSCODE","CLAIMS","NCLASS","CAT","SUBCAT","CMADE","CRECEIVE","RATIOCIT","GENERAL","ORIGINAL","FWDAPLAG","BCKGTLAG","SELFCTUB","SELFCTLB","SECDUPBD","SECDLWBD"
        # Se puede acceder al mapa de países con MRCountryPatents.country_map
        ...

if __name__ == '__main__':
    # Cargar el mapa de países
    with open('country_codes.txt') as f:
        for line in f:
            (code, name) = line.strip().split('\t')
            MRCountryPatents.country_map[code] = name

    job = MRCountryPatents()
    job.run()
