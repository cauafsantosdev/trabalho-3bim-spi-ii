import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from csv_read_tool import APOSENTADOS, CARREIRAS, importar, ler_registros


def escrever_fonte(diretorio, fonte, linhas):
    caminho = diretorio / fonte.arquivo
    terminador = ";" if fonte == CARREIRAS else ""
    with caminho.open("w", encoding="latin-1") as arquivo:
        if fonte.preambulo:
            print(fonte.preambulo, file=arquivo)
        print(";".join(cabecalho for cabecalho, _, _ in fonte.campos) + terminador, file=arquivo)
        for linha in linhas:
            campos = [valor.ljust(largura) for valor, (_, _, largura) in zip(linha, fonte.campos, strict=True)]
            print(";".join(campos) + terminador, file=arquivo)
    return caminho


class ImportacaoTest(unittest.TestCase):
    def test_portaria_com_pontuacao_e_datas(self):
        campos = ["Nome Exemplo", "***00000***", "000003", "UNIVERSIDADE FEDERAL DO RIO GRANDE",
                  "FURG", "00000", "DOCENTE", "A", "I", "00", "000", "VOLUNTARIA",
                  '"Artigo 3"', 'PORT. 1; INCISO "A"; ART. 2', "10082025", "APOSENTADORIA",
                  "", "12.345,67"]
        with tempfile.TemporaryDirectory() as tmp:
            caminho = escrever_fonte(Path(tmp), APOSENTADOS, [campos])
            registro, = ler_registros(APOSENTADOS, caminho)
        self.assertEqual(len(registro), 18)
        self.assertEqual(registro[2:13], campos[2:13])
        self.assertEqual(registro[13:], [campos[13], date(2025, 8, 10), campos[15], None, "12345.67"])

    def test_carga_preserva_vinculo_sem_nome_e_separa_total(self):
        vinculo = ["", "***00000***", "001", "DOCENTE", "RS", "UNIVERSIDADE FEDERAL DO RIO GRANDE", "08", "2.000,03"]
        total = ["TOTAL DA CARREIRA 001:", "", "", "", "", "", "", "2.000,03"]
        cur = MagicMock()
        cur.fetchone.return_value = None
        with tempfile.TemporaryDirectory() as tmp:
            caminho = escrever_fonte(Path(tmp), CARREIRAS, [vinculo, total])
            self.assertTrue(importar(cur, CARREIRAS, caminho, "hash"))
            copia = cur.copy.return_value.__enter__.return_value
            copia.write_row.assert_called_once_with([*vinculo[:-1], "2000.03"])
            self.assertEqual(cur.executemany.call_args.args[1], [(total[0], "2000.03")])
            cur.fetchone.return_value = ("hash",)
            self.assertFalse(importar(cur, CARREIRAS, caminho, "hash"))
            self.assertEqual(cur.copy.call_count, 1)

    def test_linha_incompleta_identifica_arquivo_e_posicao(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = escrever_fonte(Path(tmp), CARREIRAS, [])
            with caminho.open("a", encoding="latin-1") as arquivo:
                print("linha;incompleta", file=arquivo)
            with self.assertRaisesRegex(ValueError, r"CARREIRA_082026\.csv, linha 3"):
                list(ler_registros(CARREIRAS, caminho))
