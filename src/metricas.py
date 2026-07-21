"""
Métricas de comparação entre pedidos Liberados (aguardando montagem) e
Montados (já roteirizados/expedidos).

Importante: Liberados e Montados são dois RECORTES DIFERENTES no tempo
(um pedido sai da lista de liberados quando é montado), então a
comparação é feita por VOLUME/RITMO por estado, não pedido a pedido.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

FAIXAS_AGING = [
    (0, 2, "0-2h"),
    (2, 6, "2-6h"),
    (6, 12, "6-12h"),
    (12, 24, "12-24h"),
    (24, np.inf, "24h+"),
]


def pedidos_nao_montados(df_liberados: pd.DataFrame, df_montados: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna só os pedidos liberados que NÃO aparecem no arquivo de montados
    (cruzando por estado + numero_pedido). São os que realmente ficaram
    pendentes/pra trás — o arquivo de Liberados pode trazer também pedidos
    que já foram montados, então não dá pra tratar tudo que está lá como pendência.
    """
    if df_liberados.empty:
        return df_liberados.copy()
    if df_montados.empty:
        return df_liberados.copy()

    chave_montados = df_montados[["estado", "numero_pedido"]].drop_duplicates().copy()
    chave_montados["_montado"] = True
    merged = df_liberados.merge(chave_montados, on=["estado", "numero_pedido"], how="left")
    pendentes = merged[merged["_montado"].isna()].drop(columns=["_montado"])
    return pendentes.reset_index(drop=True)


def resumo_pendentes(df_pendentes: pd.DataFrame) -> pd.DataFrame:
    """Total de pedidos, peso e valor realmente pendentes (não montados ainda) por estado."""
    if df_pendentes.empty:
        return pd.DataFrame(columns=["estado", "pedidos_pendentes", "peso_pendente", "valor_pendente"])
    g = df_pendentes.groupby("estado").agg(
        pedidos_pendentes=("numero_pedido", "nunique"),
        peso_pendente=("peso", "sum"),
        valor_pendente=("valor", "sum"),
    ).reset_index()
    return g



    """Total de pedidos, peso e valor pendentes (liberados) por estado."""
    if df_liberados.empty:
        return pd.DataFrame(columns=["estado", "pedidos_liberados", "peso_liberado", "valor_liberado"])
    g = df_liberados.groupby("estado").agg(
        pedidos_liberados=("numero_pedido", "nunique"),
        peso_liberado=("peso", "sum"),
        valor_liberado=("valor", "sum"),
    ).reset_index()
    return g


def resumo_montados(df_montados: pd.DataFrame) -> pd.DataFrame:
    """Total de pedidos, peso e valor já montados por estado (neste snapshot)."""
    if df_montados.empty:
        return pd.DataFrame(columns=["estado", "pedidos_montados", "peso_montado", "valor_montado"])
    g = df_montados.groupby("estado").agg(
        pedidos_montados=("numero_pedido", "nunique"),
        peso_montado=("peso", "sum"),
        valor_montado=("valor", "sum"),
    ).reset_index()
    return g


def tabela_detalhada_por_estado(df_pendentes: pd.DataFrame, df_montados: pd.DataFrame) -> pd.DataFrame:
    """
    Tabela organizada por estado, com 3 linhas cada:
      Montados   -> pedidos, peso, valor
      Liberados  -> pedidos, peso, valor  (pendentes reais, que ainda não foram montados)
      TOTAL      -> soma das duas
    """
    pend = resumo_pendentes(df_pendentes).rename(
        columns={"pedidos_pendentes": "pedidos", "peso_pendente": "peso", "valor_pendente": "valor"}
    )
    mont = resumo_montados(df_montados).rename(
        columns={"pedidos_montados": "pedidos", "peso_montado": "peso", "valor_montado": "valor"}
    )

    todos_estados = sorted(set(pend["estado"]).union(set(mont["estado"])))
    linhas = []
    for estado in todos_estados:
        lp = pend[pend["estado"] == estado]
        lm = mont[mont["estado"] == estado]
        p_pedidos = float(lp["pedidos"].sum()) if not lp.empty else 0.0
        p_peso = float(lp["peso"].sum()) if not lp.empty else 0.0
        p_valor = float(lp["valor"].sum()) if not lp.empty else 0.0
        m_pedidos = float(lm["pedidos"].sum()) if not lm.empty else 0.0
        m_peso = float(lm["peso"].sum()) if not lm.empty else 0.0
        m_valor = float(lm["valor"].sum()) if not lm.empty else 0.0

        linhas.append({"estado": estado, "categoria": "Montados", "pedidos": m_pedidos, "peso": m_peso, "valor": m_valor})
        linhas.append({"estado": estado, "categoria": "Liberados (pendentes)", "pedidos": p_pedidos, "peso": p_peso, "valor": p_valor})
        linhas.append({"estado": estado, "categoria": "TOTAL", "pedidos": m_pedidos + p_pedidos, "peso": m_peso + p_peso, "valor": m_valor + p_valor})

    return pd.DataFrame(linhas)


def comparativo_por_estado(df_pendentes: pd.DataFrame, df_montados: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por estado: pendentes reais x montados lado a lado + % já montado."""
    bl = resumo_pendentes(df_pendentes)
    mt = resumo_montados(df_montados)
    comp = pd.merge(bl, mt, on="estado", how="outer").fillna(0)
    total = comp["pedidos_pendentes"] + comp["pedidos_montados"]
    comp["pct_montado"] = np.where(total > 0, comp["pedidos_montados"] / total * 100, 0)
    return comp.sort_values("estado").reset_index(drop=True)


def calcular_aging(df_liberados: pd.DataFrame, agora: pd.Timestamp) -> pd.DataFrame:
    """Adiciona idade em horas e faixa de aging a cada pedido liberado pendente."""
    if df_liberados.empty:
        return df_liberados.assign(idade_horas=pd.Series(dtype=float), faixa_aging=pd.Series(dtype=str))
    out = df_liberados.copy()
    out["idade_horas"] = (agora - out["data_hora_liberacao"]).dt.total_seconds() / 3600
    out["idade_horas"] = out["idade_horas"].clip(lower=0)

    def faixa(h):
        if pd.isna(h):
            return "sem data"
        for lo, hi, nome in FAIXAS_AGING:
            if lo <= h < hi:
                return nome
        return "24h+"

    out["faixa_aging"] = out["idade_horas"].apply(faixa)
    return out


def status_corte(df_liberados_aging: pd.DataFrame, corte_config: dict, agora: pd.Timestamp) -> pd.DataFrame:
    """
    Marca cada pedido liberado como 'atrasado' (passou do corte e ainda não foi montado)
    ou 'dentro do prazo', considerando a configuração de corte por estado.
    Estados sem corte definido (tem_corte=False) nunca ficam 'atrasado'.
    """
    if df_liberados_aging.empty:
        return df_liberados_aging.assign(status_corte=pd.Series(dtype=str))

    out = df_liberados_aging.copy()

    def calc(row):
        cfg = corte_config.get(row["estado"], {"tem_corte": False, "hora_corte": None})
        if not cfg.get("tem_corte"):
            return "sem corte"
        hora_corte = cfg.get("hora_corte")
        if not hora_corte:
            return "sem corte"
        h, m = map(int, hora_corte.split(":"))
        corte_hoje = agora.normalize() + pd.Timedelta(hours=h, minutes=m)
        if agora >= corte_hoje and row["data_hora_liberacao"] <= corte_hoje:
            return "atrasado"
        return "dentro do prazo"

    out["status_corte"] = out.apply(calc, axis=1)
    return out


def resumo_aging_por_estado(df_liberados_aging: pd.DataFrame) -> pd.DataFrame:
    if df_liberados_aging.empty:
        return pd.DataFrame(columns=["estado", "faixa_aging", "pedidos"])
    return (
        df_liberados_aging.groupby(["estado", "faixa_aging"])
        .agg(pedidos=("numero_pedido", "nunique"))
        .reset_index()
    )
