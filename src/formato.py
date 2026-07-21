"""Formatação de números no padrão brasileiro para exibição no app."""
from __future__ import annotations

import pandas as pd


def _milhar_br(valor: float, casas: int) -> str:
    if pd.isna(valor):
        return "-"
    s = f"{valor:,.{casas}f}"
    # troca separador de milhar (,) e decimal (.) do padrão US para o BR
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return s


def fmt_moeda(valor: float) -> str:
    """Ex: 727797.04 -> 'R$ 727.797,04'"""
    return f"R$ {_milhar_br(valor, 2)}"


def fmt_peso(valor: float) -> str:
    """Ex: 39206.8853 -> '39.206,89 kg'"""
    return f"{_milhar_br(valor, 2)} kg"


def fmt_num(valor: float) -> str:
    """Ex: 1792 -> '1.792'"""
    if pd.isna(valor):
        return "-"
    return _milhar_br(round(valor), 0)


def fmt_pct(valor: float) -> str:
    """Ex: 46.3889 -> '46,4%'"""
    if pd.isna(valor):
        return "-"
    return f"{_milhar_br(valor, 1)}%"


def formatar_tabela(df: pd.DataFrame, colunas_moeda=(), colunas_peso=(), colunas_num=(), colunas_pct=()) -> pd.DataFrame:
    """Retorna uma cópia do dataframe com as colunas indicadas formatadas como texto BR.
    Use só para exibição (st.dataframe) — não para cálculo, já que vira string."""
    out = df.copy()
    for c in colunas_moeda:
        if c in out.columns:
            out[c] = out[c].apply(fmt_moeda)
    for c in colunas_peso:
        if c in out.columns:
            out[c] = out[c].apply(fmt_peso)
    for c in colunas_num:
        if c in out.columns:
            out[c] = out[c].apply(fmt_num)
    for c in colunas_pct:
        if c in out.columns:
            out[c] = out[c].apply(fmt_pct)
    return out
