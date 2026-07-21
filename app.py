import streamlit as st
import pandas as pd
import plotly.express as px
import streamlit.components.v1 as components

from config.estados import ESTADOS, CORTE_PADRAO, detectar_estado, detectar_tipo
from src.etl import ler_excel, montar_snapshot
from src import metricas
from src.formato import fmt_num, fmt_pct, formatar_tabela
from src.datagrid import render_datagrid
from src.tema import CSS_FUNDO_FUTURISTA

st.set_page_config(page_title="Liberados x Montados", layout="wide")
st.markdown(CSS_FUNDO_FUTURISTA, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Google Sheets é opcional: se não estiver configurado em st.secrets, o app
# ainda funciona (só não guarda histórico entre sessões).
# ---------------------------------------------------------------------------
GSHEETS_OK = "gcp_service_account" in st.secrets and "gsheets" in st.secrets
if GSHEETS_OK:
    from src import gsheets

st.title("📦 Liberados x Montados")
st.caption("Comparação de pedidos liberados (aguardando montagem) x pedidos montados, por estado.")

if not GSHEETS_OK:
    st.warning(
        "Google Sheets não está configurado em `st.secrets` — o histórico intradiário "
        "não será salvo nesta sessão. Veja o README para configurar.",
        icon="⚠️",
    )

# ---------------------------------------------------------------------------
# Configuração de corte (sidebar)
# ---------------------------------------------------------------------------
if "corte_config" not in st.session_state:
    if GSHEETS_OK:
        st.session_state.corte_config = gsheets.carregar_config_corte(CORTE_PADRAO)
    else:
        st.session_state.corte_config = dict(CORTE_PADRAO)

with st.sidebar:
    st.header("⚙️ Configuração de corte")
    st.caption("Ajuste por estado. Estados 'sem corte' nunca entram como atrasado.")
    novo_config = {}
    for estado, nome in ESTADOS.items():
        cfg = st.session_state.corte_config.get(estado, {"tem_corte": False, "hora_corte": None})
        tem_corte = st.checkbox(f"{nome} tem corte", value=cfg["tem_corte"], key=f"chk_{estado}")
        hora_corte = None
        if tem_corte:
            hora_default = cfg.get("hora_corte") or "14:00"
            hora_corte = st.text_input(
                f"Horário de corte ({nome})", value=hora_default, key=f"hora_{estado}",
                help="Formato HH:MM"
            )
        novo_config[estado] = {"tem_corte": tem_corte, "hora_corte": hora_corte}

    if st.button("💾 Salvar configuração de corte"):
        st.session_state.corte_config = novo_config
        if GSHEETS_OK:
            gsheets.salvar_config_corte(novo_config)
        st.success("Configuração salva.")

# ---------------------------------------------------------------------------
# Upload dos arquivos
# ---------------------------------------------------------------------------
st.subheader("1. Upload dos arquivos deste snapshot")
uploads = st.file_uploader(
    "Envie os arquivos LIBERADOS_*.xls e MONTADOS_*.xlsx de uma vez (pode selecionar vários)",
    type=["xls", "xlsx"],
    accept_multiple_files=True,
)

arquivos_liberados = {}
arquivos_montados = {}

if uploads:
    st.write("Confirme o estado e o tipo detectados para cada arquivo:")
    for f in uploads:
        col1, col2, col3 = st.columns([3, 2, 2])
        estado_sugerido = detectar_estado(f.name) or list(ESTADOS.keys())[0]
        tipo_sugerido = detectar_tipo(f.name) or "liberado"
        with col1:
            st.text(f.name)
        with col2:
            estado_escolhido = st.selectbox(
                "Estado", list(ESTADOS.keys()),
                index=list(ESTADOS.keys()).index(estado_sugerido),
                key=f"estado_{f.name}",
                format_func=lambda e: ESTADOS[e],
            )
        with col3:
            tipo_escolhido = st.selectbox(
                "Tipo", ["liberado", "montado"],
                index=0 if tipo_sugerido == "liberado" else 1,
                key=f"tipo_{f.name}",
            )
        try:
            df = ler_excel(f)
        except Exception as e:
            st.error(f"Não consegui ler {f.name}: {e}")
            continue
        if tipo_escolhido == "liberado":
            arquivos_liberados[estado_escolhido] = df
        else:
            arquivos_montados[estado_escolhido] = df

# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------
if arquivos_liberados or arquivos_montados:
    try:
        df_lib, df_mont, avisos = montar_snapshot(arquivos_liberados, arquivos_montados)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    for aviso in avisos:
        st.warning(f"⚠️ {aviso}", icon="⚠️")

    agora = pd.Timestamp.now()
    df_pendentes = metricas.pedidos_nao_montados(df_lib, df_mont)
    df_lib_aging = metricas.calcular_aging(df_pendentes, agora)
    df_lib_corte = metricas.status_corte(df_lib_aging, st.session_state.corte_config, agora)
    comparativo = metricas.comparativo_por_estado(df_pendentes, df_mont)
    tabela_estado = metricas.tabela_detalhada_por_estado(df_pendentes, df_mont)

    st.subheader("2. Panorama deste snapshot")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pedidos pendentes", fmt_num(comparativo["pedidos_pendentes"].sum()))
    c2.metric("Pedidos montados", fmt_num(comparativo["pedidos_montados"].sum()))
    atrasados = (df_lib_corte["status_corte"] == "atrasado").sum() if not df_lib_corte.empty else 0
    c3.metric("Liberados atrasados (passou do corte)", fmt_num(atrasados))
    pct_geral = (
        comparativo["pedidos_montados"].sum()
        / max(comparativo["pedidos_montados"].sum() + comparativo["pedidos_pendentes"].sum(), 1)
        * 100
    )
    c4.metric("% já montado (geral)", fmt_pct(pct_geral))

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Comparativo por estado", "Aging dos pendentes", "Status de corte", "Histórico do dia"]
    )

    # -----------------------------------------------------------------------
    with tab1:
        st.markdown("#### 📊 Montados x Liberados x Total, por estado")
        st.markdown(
            "<div style='display:flex; gap:18px; margin:4px 0 16px 0; font-size:13px; color:#2f6b46;'>"
            "<span>🟩 <b>Montados</b></span>"
            "<span>🟢 <b>Liberados</b> (pendentes)</span>"
            "<span>🟦 <b>TOTAL</b></span>"
            "</div>",
            unsafe_allow_html=True,
        )

        estados_lista = list(tabela_estado["estado"].unique())
        for i in range(0, len(estados_lista), 2):
            par = estados_lista[i:i + 2]
            colunas_grid = st.columns(len(par))
            for col, estado in zip(colunas_grid, par):
                with col:
                    bloco = tabela_estado[tabela_estado["estado"] == estado].drop(columns="estado")
                    bloco_fmt = formatar_tabela(
                        bloco, colunas_moeda=["valor"], colunas_peso=["peso"], colunas_num=["pedidos"],
                    )
                    grid_html, altura = render_datagrid(
                        bloco_fmt, key=f"estado_{estado}", titulo=ESTADOS.get(estado, estado),
                        altura_max=160, linhas_por_pagina=3, colorir_categoria=True,
                    )
                    components.html(grid_html, height=altura, scrolling=False)

        st.markdown("<br>", unsafe_allow_html=True)
        fig = px.bar(
            comparativo.melt(
                id_vars="estado",
                value_vars=["pedidos_pendentes", "pedidos_montados"],
                var_name="tipo", value_name="pedidos",
            ),
            x="estado", y="pedidos", color="tipo", barmode="group",
            title="Pedidos pendentes x montados por estado",
        )
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------
    with tab2:
        if df_lib_aging.empty:
            st.info("Sem pedidos liberados neste snapshot.")
        else:
            resumo_aging = metricas.resumo_aging_por_estado(df_lib_aging)
            fig2 = px.bar(
                resumo_aging, x="estado", y="pedidos", color="faixa_aging",
                title="Idade dos pedidos liberados pendentes",
                category_orders={"faixa_aging": ["0-2h", "2-6h", "6-12h", "12-24h", "24h+", "sem data"]},
            )
            st.plotly_chart(fig2, use_container_width=True)
            tabela_aging = df_lib_aging[[
                "numero_pedido", "estado", "cliente", "cidade", "data_hora_liberacao",
                "idade_horas", "faixa_aging", "peso", "valor",
            ]].sort_values("idade_horas", ascending=False)
            tabela_aging = formatar_tabela(tabela_aging, colunas_moeda=["valor"], colunas_peso=["peso"])
            tabela_aging["idade_horas"] = tabela_aging["idade_horas"].round(1)
            grid_html, altura = render_datagrid(
                tabela_aging, key="aging", altura_max=420, linhas_por_pagina=10,
            )
            components.html(grid_html, height=altura, scrolling=False)

    # -----------------------------------------------------------------------
    with tab3:
        if df_lib_corte.empty:
            st.info("Sem pedidos liberados neste snapshot.")
        else:
            fig3 = px.histogram(
                df_lib_corte, x="estado", color="status_corte", barmode="group",
                title="Status de corte por estado",
            )
            st.plotly_chart(fig3, use_container_width=True)
            tabela_atrasados = df_lib_corte[df_lib_corte["status_corte"] == "atrasado"][[
                "numero_pedido", "estado", "cliente", "cidade", "data_hora_liberacao",
                "idade_horas", "peso", "valor",
            ]]
            tabela_atrasados = formatar_tabela(tabela_atrasados, colunas_moeda=["valor"], colunas_peso=["peso"])
            tabela_atrasados["idade_horas"] = tabela_atrasados["idade_horas"].round(1)
            grid_html, altura = render_datagrid(
                tabela_atrasados, key="atrasados", altura_max=420, linhas_por_pagina=10,
            )
            components.html(grid_html, height=altura, scrolling=False)

    # -----------------------------------------------------------------------
    with tab4:
        if GSHEETS_OK:
            if st.button("💾 Salvar este snapshot no histórico"):
                gsheets.salvar_snapshot(comparativo, agora)
                st.cache_data.clear()
                st.success("Snapshot salvo no histórico.")
            historico = gsheets.carregar_historico()
            if historico.empty:
                st.info("Ainda não há snapshots salvos no histórico.")
            else:
                fig4 = px.line(
                    historico.sort_values("timestamp"),
                    x="timestamp", y="pedidos_pendentes", color="estado",
                    title="Evolução dos pedidos pendentes ao longo do tempo",
                    markers=True,
                )
                st.plotly_chart(fig4, use_container_width=True)
                historico_fmt = formatar_tabela(
                    historico.sort_values("timestamp", ascending=False),
                    colunas_moeda=["valor_pendente", "valor_montado"],
                    colunas_peso=["peso_pendente", "peso_montado"],
                    colunas_num=["pedidos_pendentes", "pedidos_montados"],
                    colunas_pct=["pct_montado"],
                )
                grid_html, altura = render_datagrid(
                    historico_fmt, key="historico", altura_max=420, linhas_por_pagina=10,
                )
                components.html(grid_html, height=altura, scrolling=False)
        else:
            st.info("Configure o Google Sheets (veja o README) para habilitar o histórico intradiário.")
else:
    st.info("Envie os arquivos de Liberados e/ou Montados acima para começar.")
