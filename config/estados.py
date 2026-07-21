"""
Configuração central dos estados/operações acompanhados no dashboard.

IMPORTANTE sobre o horário de corte:
Não temos as regras reais de corte de cada estado, então os valores abaixo
são apenas um PONTO DE PARTIDA (todos como "sem corte definido"). Ajuste
pela tela de "Configurações" do app (os valores ficam salvos na aba
CONFIG da planilha do Google Sheets) ou editando este arquivo direto.
"""

# Código interno -> nome de exibição
ESTADOS = {
    "AM": "Amazonas",
    "BA": "Bahia",
    "DF": "Distrito Federal",
    "MG_ES": "Minas Gerais / Espírito Santo",
    "SP": "São Paulo",
    "SP_WFS": "SP (WFOOD)",
}

# Configuração padrão de corte por estado.
# tem_corte: se False, o estado é tratado como "sem horário de corte"
#            (ex: operações fluviais/rotas especiais) e nunca entra
#            como "atrasado" nas métricas de corte.
# hora_corte: horário local no formato "HH:MM", só é usado se tem_corte=True.
CORTE_PADRAO = {
    "AM":    {"tem_corte": False, "hora_corte": None},   # ex: operação fluvial, sem corte fixo
    "BA":    {"tem_corte": True,  "hora_corte": "14:00"},
    "DF":    {"tem_corte": True,  "hora_corte": "14:00"},
    "MG_ES": {"tem_corte": True,  "hora_corte": "14:00"},
    "SP":    {"tem_corte": True,  "hora_corte": "14:00"},
    "SP_WFS":{"tem_corte": True,  "hora_corte": "14:00"},
}

# Padrões usados para detectar automaticamente estado/tipo pelo nome do arquivo.
# A detecção é só uma sugestão inicial — o usuário sempre confirma/ajusta na tela de upload.
PADROES_ARQUIVO = [
    ("SP_WFS", ["WFS"]),
    ("MG_ES", ["MG_ES", "MG.ES", "MGES"]),
    ("DF", ["D_F", "D.F", "_DF", "DF_"]),
    ("BA", ["_BA", "BA_", "BA."]),
    ("AM", ["_AM", "AM_", "AM."]),
    ("SP", ["_SP", "SP_", "SP."]),  # checar por último (substring de SP_WFS)
]


def detectar_estado(nome_arquivo: str) -> str | None:
    nome = nome_arquivo.upper()
    for estado, tokens in PADROES_ARQUIVO:
        if any(t in nome for t in tokens):
            return estado
    return None


def detectar_tipo(nome_arquivo: str) -> str | None:
    nome = nome_arquivo.upper()
    if "LIBERADO" in nome:
        return "liberado"
    if "MONTADO" in nome:
        return "montado"
    return None
