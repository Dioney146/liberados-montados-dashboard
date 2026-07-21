"""
ETL: leitura dos arquivos brutos de Liberados e Montados e normalização
para um formato único, comum aos dois lados, pronto para cálculo de métricas.

Baseado na estrutura real observada nos arquivos de origem:

LIBERADOS (colunas): NUMPED, CODCLI, NUMNOTA, CODFILIAL, NOMECLIENTE, POSICAO,
    DATA, HORA, MINUTO, DTENTREGA, NOMERCA, NOMESUP, PESOBRUTOTOT, VLTOTAL,
    CIDADE, PRACA, NUMCARREGAMENTO, DESTINO, PLACA, LONGITUDE, LATITUDE

MONTADOS (colunas): FILIAL, Estado da Ordem, Cliente, Descrição da rota,
    Instruções especiais, Número do pedido, Entrega Valor, Entrega Peso,
    Entrega Volume, Sessão de roteirização, Cidade, Data de término,
    Gerenciado Por, Itens do pedido, Tipo, CODROTA, Classe da Ordem
"""
from __future__ import annotations

import io
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Helpers de parsing
# ---------------------------------------------------------------------------

def parse_numero_br(valor) -> float:
    """Converte números no formato brasileiro (1.234,56) ou já numéricos para float."""
    if pd.isna(valor):
        return np.nan
    if isinstance(valor, (int, float, np.integer, np.floating)):
        return float(valor)
    s = str(valor).strip()
    if s == "" or s.lower() == "nan":
        return np.nan
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_numero_pedido(valor) -> "int | None":
    """Número do pedido, sempre como int (ou None se inválido/vazio)."""
    if pd.isna(valor):
        return None
    try:
        return int(float(str(valor).strip()))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Leitura bruta
# ---------------------------------------------------------------------------

def ler_excel(fonte) -> pd.DataFrame:
    """Lê um .xls/.xlsx (path ou objeto tipo arquivo) na primeira planilha."""
    return pd.read_excel(fonte)


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

COLUNAS_LIBERADOS_ESPERADAS = {
    "NUMPED", "CODCLI", "CODFILIAL", "NOMECLIENTE", "DATA", "HORA", "MINUTO",
    "DTENTREGA", "NOMERCA", "NOMESUP", "PESOBRUTOTOT", "VLTOTAL", "CIDADE",
    "PRACA", "NUMCARREGAMENTO", "DESTINO",
}

COLUNAS_MONTADOS_ESPERADAS = {
    "FILIAL", "Estado da Ordem", "Cliente", "Número do pedido",
    "Entrega Valor", "Entrega Peso", "Cidade", "Data de término",
    "Gerenciado Por", "CODROTA",
}


def normalizar_liberados(df: pd.DataFrame, estado: str) -> tuple[pd.DataFrame, int]:
    faltando = COLUNAS_LIBERADOS_ESPERADAS - set(df.columns)
    if faltando:
        raise ValueError(
            f"Arquivo de Liberados ({estado}) não tem as colunas esperadas: {sorted(faltando)}"
        )

    # Algumas extrações vêm com uma linha de RODAPÉ/TOTAL no final (soma de peso/valor
    # de todas as linhas). Essa linha não tem cliente nem data, só os totais — se não for
    # removida, ela é somada junto com os pedidos de verdade e dobra peso/valor.
    linhas_antes = len(df)
    df = df[df["NOMECLIENTE"].notna() & df["CODCLI"].notna()].copy()
    n_removidas = linhas_antes - len(df)

    out = pd.DataFrame()
    out["numero_pedido"] = df["NUMPED"].apply(parse_numero_pedido)
    out["codigo_cliente"] = df["CODCLI"]
    out["cliente"] = df["NOMECLIENTE"]
    out["filial"] = df["CODFILIAL"]
    out["cidade"] = df["CIDADE"]
    out["praca"] = df["PRACA"]
    out["destino"] = df["DESTINO"]
    out["representante"] = df["NOMERCA"]
    out["supervisor"] = df["NOMESUP"]
    out["peso"] = df["PESOBRUTOTOT"].apply(parse_numero_br)
    out["valor"] = df["VLTOTAL"].apply(parse_numero_br)
    out["data_entrega_prevista"] = pd.to_datetime(df["DTENTREGA"], errors="coerce")

    data = pd.to_datetime(df["DATA"], errors="coerce")
    hora = pd.to_numeric(df["HORA"], errors="coerce").fillna(0).clip(0, 23).astype(int)
    minuto = pd.to_numeric(df["MINUTO"], errors="coerce").fillna(0).clip(0, 59).astype(int)
    out["data_hora_liberacao"] = data + pd.to_timedelta(hora, unit="h") + pd.to_timedelta(minuto, unit="m")

    out["estado"] = estado
    out["origem"] = "liberado"
    out = out.dropna(subset=["numero_pedido"]).reset_index(drop=True)
    return out, n_removidas


def normalizar_montados(df: pd.DataFrame, estado: str) -> tuple[pd.DataFrame, int]:
    faltando = COLUNAS_MONTADOS_ESPERADAS - set(df.columns)
    if faltando:
        raise ValueError(
            f"Arquivo de Montados ({estado}) não tem as colunas esperadas: {sorted(faltando)}"
        )

    # Mesmo cuidado do lado de Montados: linha de rodapé/total sem cliente.
    linhas_antes = len(df)
    cliente_valido = df["Cliente"].notna() & (df["Cliente"].astype(str).str.strip() != "")
    df = df[cliente_valido].copy()
    n_removidas = linhas_antes - len(df)

    out = pd.DataFrame()
    out["numero_pedido"] = df["Número do pedido"].apply(parse_numero_pedido)
    out["cliente"] = df["Cliente"]
    out["filial"] = df["FILIAL"]
    out["cidade"] = df["Cidade"]
    out["status_montagem"] = df["Estado da Ordem"].astype(str).str.strip()
    out["peso"] = df["Entrega Peso"].apply(parse_numero_br)
    out["valor"] = df["Entrega Valor"].apply(parse_numero_br)
    out["gerenciado_por"] = df["Gerenciado Por"]
    out["cod_rota"] = df["CODROTA"]
    out["data_termino"] = pd.to_datetime(df["Data de término"], errors="coerce", dayfirst=True)

    out["estado"] = estado
    out["origem"] = "montado"
    out = out.dropna(subset=["numero_pedido"]).reset_index(drop=True)
    return out, n_removidas


# ---------------------------------------------------------------------------
# Orquestração de um snapshot (lote de uploads de uma vez)
# ---------------------------------------------------------------------------

def montar_snapshot(arquivos_liberados: dict, arquivos_montados: dict):
    """
    arquivos_liberados / arquivos_montados: dict {estado: DataFrame já lido do excel}
    Retorna (df_liberados_consolidado, df_montados_consolidado, avisos)
    onde 'avisos' é uma lista de strings sobre linhas de rodapé/total removidas.
    """
    libs = []
    montados = []
    avisos = []

    for estado, df in arquivos_liberados.items():
        norm, n_removidas = normalizar_liberados(df, estado)
        libs.append(norm)
        if n_removidas:
            avisos.append(
                f"Liberados ({estado}): {n_removidas} linha(s) de rodapé/total detectada(s) "
                f"e removida(s) automaticamente (sem cliente/código de cliente)."
            )

    for estado, df in arquivos_montados.items():
        norm, n_removidas = normalizar_montados(df, estado)
        montados.append(norm)
        if n_removidas:
            avisos.append(
                f"Montados ({estado}): {n_removidas} linha(s) de rodapé/total detectada(s) "
                f"e removida(s) automaticamente (sem cliente)."
            )

    df_lib = pd.concat(libs, ignore_index=True) if libs else pd.DataFrame()
    df_mont = pd.concat(montados, ignore_index=True) if montados else pd.DataFrame()
    return df_lib, df_mont, avisos
