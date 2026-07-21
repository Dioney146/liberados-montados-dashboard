"""
Integração com Google Sheets, usada como:
  1) histórico de snapshots ao longo do dia (aba HISTORICO)
  2) configuração de horário de corte por estado, editável no app (aba CONFIG_CORTE)

Requer uma conta de serviço do Google Cloud com acesso à planilha.
Veja o README.md para o passo a passo de configuração.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

ABA_HISTORICO = "HISTORICO"
ABA_CONFIG = "CONFIG_CORTE"

COLUNAS_HISTORICO = [
    "timestamp", "estado", "pedidos_pendentes", "peso_pendente", "valor_pendente",
    "pedidos_montados", "peso_montado", "valor_montado", "pct_montado",
]

COLUNAS_CONFIG = ["estado", "tem_corte", "hora_corte"]


@st.cache_resource(show_spinner=False)
def _client():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def _abrir_planilha():
    client = _client()
    sheet_id = st.secrets["gsheets"]["spreadsheet_id"]
    return client.open_by_key(sheet_id)


def _garantir_aba(sh, nome: str, colunas: list[str]):
    try:
        ws = sh.worksheet(nome)
    except Exception:
        ws = sh.add_worksheet(title=nome, rows=1000, cols=max(10, len(colunas)))
        ws.append_row(colunas)
    return ws


def salvar_snapshot(df_comparativo: pd.DataFrame, timestamp: pd.Timestamp):
    """Acrescenta uma linha por estado na aba de histórico."""
    sh = _abrir_planilha()
    ws = _garantir_aba(sh, ABA_HISTORICO, COLUNAS_HISTORICO)

    linhas = []
    for _, row in df_comparativo.iterrows():
        linhas.append([
            timestamp.isoformat(),
            row["estado"],
            int(row.get("pedidos_pendentes", 0)),
            float(row.get("peso_pendente", 0)),
            float(row.get("valor_pendente", 0)),
            int(row.get("pedidos_montados", 0)),
            float(row.get("peso_montado", 0)),
            float(row.get("valor_montado", 0)),
            float(row.get("pct_montado", 0)),
        ])
    if linhas:
        ws.append_rows(linhas, value_input_option="USER_ENTERED")


@st.cache_data(ttl=60, show_spinner=False)
def carregar_historico() -> pd.DataFrame:
    sh = _abrir_planilha()
    ws = _garantir_aba(sh, ABA_HISTORICO, COLUNAS_HISTORICO)
    registros = ws.get_all_records()
    df = pd.DataFrame(registros)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def carregar_config_corte(default: dict) -> dict:
    sh = _abrir_planilha()
    ws = _garantir_aba(sh, ABA_CONFIG, COLUNAS_CONFIG)
    registros = ws.get_all_records()
    if not registros:
        salvar_config_corte(default)
        return default
    config = {}
    for r in registros:
        config[r["estado"]] = {
            "tem_corte": str(r["tem_corte"]).strip().upper() in ("TRUE", "1", "SIM", "VERDADEIRO"),
            "hora_corte": r["hora_corte"] or None,
        }
    return config


def salvar_config_corte(config: dict):
    sh = _abrir_planilha()
    ws = _garantir_aba(sh, ABA_CONFIG, COLUNAS_CONFIG)
    ws.clear()
    ws.append_row(COLUNAS_CONFIG)
    linhas = [[estado, cfg["tem_corte"], cfg.get("hora_corte") or ""] for estado, cfg in config.items()]
    ws.append_rows(linhas, value_input_option="USER_ENTERED")
