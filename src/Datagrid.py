"""
DataGrid HTML/CSS/JS "profissional" pra exibir tabelas no app — cabeçalho fixo,
hover nas linhas, linhas alternadas, paginação real (só a página atual entra
no DOM, então funciona bem mesmo com milhares de linhas) e tipografia premium.

Renderizado via streamlit.components.v1.html (não dá pra fazer isso só com
st.dataframe/Styler, que não suporta paginação nem hover real).
"""
from __future__ import annotations

import html as _html
import json
import re
import pandas as pd

_ROTULOS = {
    "categoria": "Categoria",
    "pedidos": "Pedidos",
    "peso": "Peso",
    "valor": "Valor",
    "estado": "Estado",
    "numero_pedido": "Nº Pedido",
    "cliente": "Cliente",
    "cidade": "Cidade",
    "data_hora_liberacao": "Liberado em",
    "idade_horas": "Idade (h)",
    "faixa_aging": "Faixa",
    "status_corte": "Status",
    "timestamp": "Data / Hora",
    "pedidos_pendentes": "Pedidos pendentes",
    "peso_pendente": "Peso pendente",
    "valor_pendente": "Valor pendente",
    "pedidos_montados": "Pedidos montados",
    "peso_montado": "Peso montado",
    "valor_montado": "Valor montado",
    "pct_montado": "% Montado",
}


def _rotulo(col: str) -> str:
    return _ROTULOS.get(col, col.replace("_", " ").title())


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(texto)).strip("_").lower()
    return s or "grid"


def _val(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)


def _classe_categoria(cat: str) -> str:
    if cat == "TOTAL":
        return "dg-total"
    if cat == "Montados":
        return "dg-montados"
    if cat.startswith("Liberados"):
        return "dg-liberados"
    return ""


_CSS_BASE = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

#{uid} {{
  font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif;
}}
#{uid} .dg-title {{
  font-weight: 700;
  font-size: 15px;
  color: #0b3d24;
  padding: 2px 2px 8px 2px;
  letter-spacing: .01em;
}}
#{uid} .dg-shell {{
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #d7ede1;
  box-shadow: 0 4px 18px rgba(15, 81, 50, 0.08);
  background: #ffffff;
}}
#{uid} .dg-scroll {{
  max-height: {altura}px;
  overflow: auto;
}}
#{uid} table {{
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}}
#{uid} thead th {{
  position: sticky;
  top: 0;
  z-index: 3;
  background: linear-gradient(135deg, #1c7a45, #2f9e5c 55%, #3cb873);
  color: #ffffff;
  padding: 13px 16px;
  font-size: 12.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  text-align: center;
  white-space: nowrap;
  border-bottom: 2px solid #17693b;
}}
#{uid} tbody td {{
  padding: 11px 16px;
  font-size: 13.5px;
  color: #16382a;
  text-align: center;
  white-space: nowrap;
  border-bottom: 1px solid #eef6f1;
}}
#{uid} tbody tr {{
  transition: background-color .12s ease-in-out;
}}
#{uid} tbody tr:nth-child(even) {{
  background-color: #f5fbf8;
}}
#{uid} tbody tr:hover td {{
  background-color: #dcf3e6 !important;
}}
#{uid} tbody tr.dg-total td {{
  background-color: #bfead0 !important;
  color: #0b3d24;
  font-weight: 800;
}}
#{uid} tbody tr.dg-montados td {{
  background-color: #e4f8ec;
}}
#{uid} tbody tr.dg-liberados td {{
  background-color: #f4fcf7;
}}
#{uid} .dg-pager {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 10px 12px;
  background: #f8fdfa;
  border-top: 1px solid #e4f2ea;
  font-size: 12.5px;
  color: #2f6b46;
}}
#{uid} .dg-pager button {{
  border: none;
  background: #2f9e5c;
  color: white;
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 700;
  font-size: 12.5px;
  font-family: inherit;
  transition: transform .1s ease, background .15s ease;
}}
#{uid} .dg-pager button:hover:not(:disabled) {{
  background: #237a48;
  transform: translateY(-1px);
}}
#{uid} .dg-pager button:disabled {{
  opacity: .35;
  cursor: default;
}}
#{uid} .dg-empty {{
  padding: 22px;
  text-align: center;
  color: #6b8f7c;
  font-size: 13px;
}}
"""

# Renderiza só a página atual no DOM (dados completos ficam num array JS em memória,
# não em milhares de <tr> escondidos) — assim funciona liso mesmo com muitas linhas.
_JS_TEMPLATE = """
(function() {{
  const rowsPerPage = {linhas_por_pagina};
  const dados = {dados_json};
  const classes = {classes_json};
  const tbody = document.getElementById('{uid}_body');
  const info = document.getElementById('{uid}_info');
  const prevBtn = document.getElementById('{uid}_prev');
  const nextBtn = document.getElementById('{uid}_next');
  let page = 0;
  const totalPages = Math.max(1, Math.ceil(dados.length / rowsPerPage));

  function render() {{
    tbody.innerHTML = '';
    const inicio = page * rowsPerPage;
    const fim = Math.min(inicio + rowsPerPage, dados.length);
    if (dados.length === 0) {{
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.className = 'dg-empty';
      td.colSpan = 99;
      td.textContent = 'Sem dados neste snapshot.';
      tr.appendChild(td);
      tbody.appendChild(tr);
    }}
    for (let i = inicio; i < fim; i++) {{
      const tr = document.createElement('tr');
      if (classes[i]) tr.className = classes[i];
      dados[i].forEach(valor => {{
        const td = document.createElement('td');
        td.textContent = valor;
        tr.appendChild(td);
      }});
      tbody.appendChild(tr);
    }}
    info.textContent = 'Página ' + (page + 1) + ' de ' + totalPages + ' · ' + dados.length + ' registros';
    prevBtn.disabled = page === 0;
    nextBtn.disabled = page >= totalPages - 1;
  }}
  prevBtn.onclick = () => {{ if (page > 0) {{ page--; render(); }} }};
  nextBtn.onclick = () => {{ if (page < totalPages - 1) {{ page++; render(); }} }};
  render();
}})();
"""


def render_datagrid(
    df: pd.DataFrame,
    key: str,
    titulo: str | None = None,
    altura_max: int = 360,
    linhas_por_pagina: int = 8,
    colorir_categoria: bool = False,
) -> tuple[str, int]:
    """
    Monta o HTML de um DataGrid profissional (cabeçalho fixo, hover, zebra, paginação real).
    Retorna (html, altura_sugerida_para_o_componente).
    """
    uid = f"dg_{_slug(key)}"
    n_linhas = 0 if df.empty else len(df)

    dados = []
    classes = []
    if not df.empty:
        for _, row in df.iterrows():
            dados.append([_val(v) for v in row])
            if colorir_categoria and "categoria" in df.columns:
                classes.append(_classe_categoria(str(row["categoria"])))
            else:
                classes.append("")

    headers = "".join(f"<th>{_html.escape(_rotulo(c))}</th>" for c in df.columns)
    titulo_html = f"<div class='dg-title'>{_html.escape(titulo)}</div>" if titulo else ""

    css = _CSS_BASE.format(uid=uid, altura=altura_max)
    js = _JS_TEMPLATE.format(
        uid=uid,
        linhas_por_pagina=linhas_por_pagina,
        dados_json=json.dumps(dados, ensure_ascii=False),
        classes_json=json.dumps(classes, ensure_ascii=False),
    )

    grid_html = f"""
    <div id="{uid}">
      <style>{css}</style>
      {titulo_html}
      <div class="dg-shell">
        <div class="dg-scroll">
          <table>
            <thead><tr>{headers}</tr></thead>
            <tbody id="{uid}_body"></tbody>
          </table>
        </div>
        <div class="dg-pager">
          <button id="{uid}_prev">‹ Anterior</button>
          <span id="{uid}_info"></span>
          <button id="{uid}_next">Próxima ›</button>
        </div>
      </div>
      <script>{js}</script>
    </div>
    """

    linhas_visiveis = min(n_linhas, linhas_por_pagina) if n_linhas else 1
    altura_estimada = min(altura_max, 46 + 40 * linhas_visiveis) + (34 if titulo else 0) + 56
    return grid_html, altura_estimada
