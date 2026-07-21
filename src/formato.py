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


# ---------------------------------------------------------------------------
# Estilização visual (tema verde/claro) para as tabelas do app
# ---------------------------------------------------------------------------

_VERDE_TOTAL = "background-color:#bfead0; color:#0b3d24; font-weight:700;"
_VERDE_MONTADOS = "background-color:#e4f8ec; color:#0f5132;"
_VERDE_LIBERADOS = "background-color:#f4fcf7; color:#2f6b46;"
_LINHA_ZEBRA_A = "background-color:#ffffff;"
_LINHA_ZEBRA_B = "background-color:#f2faf5;"


def estilizar_tabela_estado(df: pd.DataFrame):
    """Aplica cor por categoria (Montados / Liberados / TOTAL) numa tabela de estado,
    com texto centralizado e espaçamento maior — pensado pra ficar legível em print."""

    def cor_linha(row):
        cat = str(row.get("categoria", ""))
        if cat == "TOTAL":
            estilo = _VERDE_TOTAL
        elif cat == "Montados":
            estilo = _VERDE_MONTADOS
        elif cat.startswith("Liberados"):
            estilo = _VERDE_LIBERADOS
        else:
            estilo = ""
        return [estilo] * len(row)

    return (
        df.style
        .apply(cor_linha, axis=1)
        .set_properties(**{"text-align": "center", "font-size": "15px", "padding": "10px 14px"})
        .set_table_styles([
            {"selector": "th", "props": "background-color:#2f9e5c; color:white; font-weight:600; "
                                          "text-align:center; font-size:15px; padding:10px 14px;"},
            {"selector": "td, th", "props": "border:1px solid #d7ede1;"},
        ])
    )


def estilizar_tabela_zebra(df: pd.DataFrame):
    """Listrado leve (branco/verde bem claro) pra tabelas genéricas (histórico, aging, atrasados),
    também centralizado e com espaçamento maior."""
    df = df.reset_index(drop=True)

    def cor_linha(row):
        idx = row.name if isinstance(row.name, int) else 0
        estilo = _LINHA_ZEBRA_A if idx % 2 == 0 else _LINHA_ZEBRA_B
        return [estilo] * len(row)

    return (
        df.style
        .apply(cor_linha, axis=1)
        .set_properties(**{"text-align": "center", "font-size": "14px", "padding": "8px 12px"})
        .set_table_styles([
            {"selector": "th", "props": "background-color:#2f9e5c; color:white; font-weight:600; "
                                          "text-align:center; font-size:14px; padding:8px 12px;"},
            {"selector": "td, th", "props": "border:1px solid #d7ede1;"},
        ])
    )


def legenda_cores_estado():
    """HTML de uma legenda pequena explicando o significado das cores das tabelas de estado."""
    itens = [
        (_VERDE_MONTADOS.split(";")[0].split(":")[1], "Montados"),
        (_VERDE_LIBERADOS.split(";")[0].split(":")[1], "Liberados (pendentes)"),
        (_VERDE_TOTAL.split(";")[0].split(":")[1], "TOTAL"),
    ]
    blocos = "".join(
        f"<span style='display:inline-flex; align-items:center; margin-right:18px;'>"
        f"<span style='width:14px; height:14px; background:{cor}; border:1px solid #bbb; "
        f"border-radius:3px; display:inline-block; margin-right:6px;'></span>"
        f"<span style='font-size:13px; color:#333;'>{nome}</span></span>"
        for cor, nome in itens
    )
    return f"<div style='margin:6px 0 14px 0;'>{blocos}</div>"
