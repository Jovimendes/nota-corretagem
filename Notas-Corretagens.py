"""
Processador de Notas de Corretagem - Rico Corretora
Extrai e consolida dados por data de pregão a partir de PDFs.
"""

import re
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from collections import defaultdict

import pdfplumber
import pandas as pd


# ──────────────────────────────────────────────
# CONFIGURAÇÃO
# ──────────────────────────────────────────────
PASTA_PDFS = Path(r".\nota-corretagem") if Path(r".\nota-corretagem").exists() else Path("./nota-corretagem")
# ARQUIVO_SAIDA = PASTA_PDFS.parent / "notas_consolidadas.csv" # pasta pai
ARQUIVO_SAIDA = Path(r".\nota-corretagem") / "notas_consolidadas.csv"

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def br_to_decimal(valor_str: str) -> Decimal:
    """Converte string no formato brasileiro ('1.234,56') para Decimal."""
    limpo = valor_str.strip().replace(".", "").replace(",", ".")
    return Decimal(limpo)


def aplicar_sinal(valor: Decimal, dc: str) -> Decimal:
    """Aplica sinal: D = negativo, C = positivo."""
    return -valor if dc.strip().upper() == "D" else valor


def extrair_data_pregao(linhas: list[str]) -> str | None:
    """
    Extrai a data de pregão.
    Estrutura:
      'Nr. nota Folha Data pregão'   ← linha-âncora obrigatória
      '357.986 1 02/01/2025'         ← data é o ÚLTIMO token desta linha

    IMPORTANTE: NÃO usar re.search no texto completo — as linhas de
    negociação também contêm datas (vencimento dos contratos) que
    causariam falso-positivo (ex: 01/04/2025, 16/04/2025).
    A data de pregão só existe na linha imediatamente após o header.
    """
    for i, linha in enumerate(linhas):
        # Âncora: linha que contém TANTO 'Nr. nota' QUANTO 'Data pregão'
        if "Nr. nota" in linha and "Data pregão" in linha:
            if i + 1 < len(linhas):
                tokens = linhas[i + 1].split()
                # Último token que seja uma data DD/MM/AAAA
                for token in reversed(tokens):
                    if re.match(r"\d{2}/\d{2}/\d{4}$", token):
                        return token
    return None


def extrair_negociacoes(linhas: list[str]) -> list[dict]:
    """
    Extrai linhas da tabela 'Negociações'.
    Retorna lista de dicts: {mercadoria: str, valor: Decimal}
    """
    negociacoes = []

    # Padrão de linha de negociação:
    # C WDO G25 03/02/2025 1 6.242,00 DAY TRADE 488,92 D 0,00
    padrao = re.compile(
        r"^[CV]\s+"
        r"(WIN|WDO)\s+\S+\s+"          # mercadoria (3 letras) + vencimento curto
        r"\d{2}/\d{2}/\d{4}\s+"        # data vencimento
        r"\d+\s+"                       # quantidade
        r"[\d.,]+\s+"                   # preço/ajuste
        r"DAY TRADE\s+"                 # tipo
        r"([\d.,]+)\s+"                 # valor operação
        r"([DC])\s+"                    # D/C
    )

    for linha in linhas:
        m = padrao.match(linha.strip())
        if m:
            mercadoria = m.group(1).upper()
            valor_str = m.group(2)
            dc = m.group(3)
            try:
                valor = br_to_decimal(valor_str)
                negociacoes.append({
                    "mercadoria": mercadoria,
                    "valor": aplicar_sinal(valor, dc),
                })
            except InvalidOperation:
                continue

    return negociacoes


def extrair_custos_operacionais(linhas: list[str]) -> Decimal:
    """
    Extrai 'Total de custos operacionais' da linha de valores que segue o header.
    Estrutura:
      '+Outros Custos  Impostos  Ajuste de posição  Ajuste day trade  Total de custos operacionais'
      '0,00 0,00 0,00 | 28,00 | C 8,06 | D'
                                                    ^^^^^^^^^^^^^^^^
                                                    Total custos = último par valor|D/C
    """
    for i, linha in enumerate(linhas):
        if "Total de custos operacionais" in linha:
            # O valor está na PRÓXIMA linha
            if i + 1 < len(linhas):
                dados = linhas[i + 1]
                # Encontra TODOS os pares: valor | D/C
                pares = re.findall(r"([\d.,]+)\s*\|\s*([DC])", dados)
                if pares:
                    # O último par é o Total de custos operacionais
                    val_str, dc = pares[-1]
                    try:
                        valor = br_to_decimal(val_str)
                        return aplicar_sinal(valor, dc)
                    except InvalidOperation:
                        pass
    return Decimal("0")


def processar_pagina(page, nome_arquivo: str) -> dict | None:
    """Processa uma página individual e retorna dict com os dados extraídos."""
    texto = page.extract_text()
    if not texto:
        return None

    linhas = texto.split("\n")

    data_pregao = extrair_data_pregao(linhas)
    if not data_pregao:
        return None

    negociacoes = extrair_negociacoes(linhas)
    custos = extrair_custos_operacionais(linhas)

    total_win = sum(n["valor"] for n in negociacoes if n["mercadoria"] == "WIN")
    total_wdo = sum(n["valor"] for n in negociacoes if n["mercadoria"] == "WDO")

    return {
        "arquivo": nome_arquivo,
        "data_pregao": data_pregao,
        "total_win": total_win,
        "total_wdo": total_wdo,
        "custos_operacionais": custos,
    }


# ──────────────────────────────────────────────
# PROCESSAMENTO PRINCIPAL
# ──────────────────────────────────────────────

def processar_pdfs(pasta: Path) -> pd.DataFrame:
    """Processa todos os PDFs da pasta e retorna DataFrame consolidado."""
    acumulador: dict[tuple, dict] = defaultdict(lambda: {
        "arquivo": "",
        "total_win": Decimal("0"),
        "total_wdo": Decimal("0"),
        "custos_operacionais": Decimal("0"),
    })

    pdfs = sorted(pasta.glob("*.pdf"))
    if not pdfs:
        print(f"⚠️  Nenhum PDF encontrado em: {pasta.resolve()}")
        return pd.DataFrame()

    total_paginas = 0

    for pdf_path in pdfs:
        print(f"\n📄 Processando: {pdf_path.name}")
        with pdfplumber.open(pdf_path) as pdf:
            qtd_pags = len(pdf.pages)
            print(f"   Páginas: {qtd_pags}")
            total_paginas += qtd_pags
            for i, page in enumerate(pdf.pages, 1):
                resultado = processar_pagina(page, pdf_path.name)
                if resultado:
                    chave = (resultado["arquivo"], resultado["data_pregao"])
                    acumulador[chave]["arquivo"] = resultado["arquivo"]
                    acumulador[chave]["total_win"] += resultado["total_win"]
                    acumulador[chave]["total_wdo"] += resultado["total_wdo"]
                    acumulador[chave]["custos_operacionais"] += resultado["custos_operacionais"]
                    print(f"   ✓ Pág {i}: {resultado['data_pregao']} | "
                          f"WIN={resultado['total_win']:+.2f} | "
                          f"WDO={resultado['total_wdo']:+.2f} | "
                          f"Custos={resultado['custos_operacionais']:+.2f}")
                else:
                    print(f"   ✗ Pág {i}: dados não extraídos")

    print(f"\n📊 Total páginas processadas: {total_paginas}")
    print(f"📊 Total datas únicas:        {len(acumulador)}")

    # Monta DataFrame ordenado por data
    linhas = []
    def sort_key(item):
        data = item[0][1]          # "DD/MM/AAAA"
        d, m, a = data.split("/")
        return (a, m, d)

    for (arquivo, data_pregao), dados in sorted(acumulador.items(), key=sort_key):
        win    = dados["total_win"]
        wdo    = dados["total_wdo"]
        custos = dados["custos_operacionais"]
        total  = win + wdo + custos
        linhas.append({
            "arquivo":                      arquivo,
            "data pregão":                  data_pregao,
            "Total WIN":                    win,
            "Total WDO":                    wdo,
            "Total de custos operacionais": custos,
            "total geral":                  total,
        })

    return pd.DataFrame(linhas)


def formatar_decimal(valor: Decimal) -> str:
    """Formata Decimal com 2 casas decimais, vírgula decimal e sinal."""
    sinal = "-" if valor < 0 else ""
    partes = f"{abs(valor):.2f}".split(".")
    return f"{sinal}{partes[0]},{partes[1]}"


def exportar_csv(df: pd.DataFrame, caminho: Path):
    """Exporta o DataFrame para CSV com formatação brasileira (sep=';')."""
    colunas_num = ["Total WIN", "Total WDO", "Total de custos operacionais", "total geral"]
    df_export = df.copy()
    for col in colunas_num:
        df_export[col] = df_export[col].apply(formatar_decimal)

    df_export.to_csv(caminho, index=False, sep=";",
                     encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    print(f"\n✅ CSV exportado: {caminho.resolve()}")


# ──────────────────────────────────────────────
# EXECUÇÃO
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  PROCESSADOR DE NOTAS DE CORRETAGEM - RICO")
    print("=" * 60)

    df = processar_pdfs(PASTA_PDFS)

    if df.empty:
        print("\n❌ Nenhum dado extraído.")
    else:
        print("\n" + "=" * 60)
        print("  TABELA CONSOLIDADA")
        print("=" * 60)

        df_display = df.copy()
        for col in ["Total WIN", "Total WDO", "Total de custos operacionais", "total geral"]:
            df_display[col] = df_display[col].apply(formatar_decimal)

        print(df_display.to_string(index=False))
        print(f"\nTotal de linhas (dias de pregão): {len(df)}")

        exportar_csv(df, ARQUIVO_SAIDA)
