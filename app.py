import html
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

st.set_page_config(
    page_title="HEIWA | Explorador de Argumentos",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Design ---------------------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
.hero {padding: 1.25rem 1.4rem; border: 1px solid #e4e7ec; border-radius: 16px;
       background: linear-gradient(120deg, #f7f9fc, #ffffff); margin-bottom: 1rem;}
.hero h1 {margin: 0; font-size: 2rem; color: #182230;}
.hero p {margin: .4rem 0 0 0; color: #475467;}
.small-note {color: #667085; font-size: .88rem;}
div[data-testid="stMetric"] {border: 1px solid #eaecf0; padding: 12px 14px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>HEIWA — Explorador de Argumentos</h1>
  <p>Explore afirmações, dados e elementos argumentativos de conversas públicas.</p>
</div>
""", unsafe_allow_html=True)

# Exact labels from the supplied annotation schema, plus aliases for common variants.
COLS = {
    "conversation": ["Conversation_id", "Conversation ID", "conversation_id"],
    "text": ["Texto", "text", "Texto original"],
    "claim": [
        "Trecho que contém a afirmação (claim) extraída",
        "Trecho que contém a afirmação (claim) extraída ",
        "Claim", "claim"
    ],
    "data": ["Trecho que contém dados extraídos", "Dado", "Data"],
    "warrant": [
        "Trecho que contém justificativa (warrant) extraído",
        "Trecho que contém justificativa (warrant) extraída",
        "Warrant", "Justificativa (Warrant)"
    ],
    "rebuttal": [
        "Trecho que contém refutação (rebuttal) extraído",
        "Trecho que contém refutação (rebuttal) extraída",
        "Rebuttal", "Refutação"
    ],
    "backing": [
        "Trecho que contém Apoio adicional (backing) extraído",
        "Trecho que contém apoio adicional (backing) extraído",
        "Backing", "Apoio adicional"
    ],
    "qualifier": [
        "Trecho que contém qualificador extraído",
        "Trecho que contém qualificador (qualifier) extraído",
        "Qualifier", "Qualificador"
    ],
    "id": ["ID", "Id", "id"],
    "claim_present": ["Afirmação (claim) presente? (Sim ou Não)", "Claim presente?", "claim_present"],
    "data_present": ["Dados presente? (Sim ou Não)", "Dados presentes? (Sim ou Não)", "Data presente?", "data_present"],
    "warrant_present": ["Justificativa (Warrant) presente? (Sim ou Não)", "Warrant presente?", "warrant_present"],
    "rebuttal_present": ["Refutação (rebuttal) presente? (Sim ou Não)", "Rebuttal presente?", "rebuttal_present"],
    "backing_present": ["Apoio adicional (backing) presente? (Sim ou Não)", "Backing presente?", "backing_present"],
    "qualifier_present": ["Qualificador presente? (Sim ou Não)", "Qualifier presente?", "qualifier_present"],
    "claim_reason": ["Justificativa do trecho ser uma afirmação (claim)", "Justificativa da afirmação"],
    "data_reason": ["Justificativa do trecho conter dados", "Justificativa dos dados"],
    "warrant_reason": ["Justificativa do trecho conter justificativa (warrant)", "Justificativa do warrant"],
    "rebuttal_reason": ["Justificativa do trecho conter refutação (rebuttal)", "Justificativa do rebuttal"],
    "backing_reason": ["Justificativa do trecho conter Apoio adicional (backing)", "Justificativa do backing"],
    "qualifier_reason": ["Justificativa do trecho conter qualificador", "Justificativa do qualifier"],
}

ELEMENTS = [
    ("claim", "Afirmação (claim)", "#D92D20", "box"),
    ("data", "Dado", "#4F46E5", "dot"),
    ("warrant", "Justificativa (warrant)", "#16A34A", "dot"),
    ("rebuttal", "Refutação (rebuttal)", "#D97706", "triangle"),
    ("backing", "Apoio adicional (backing)", "#0891B2", "diamond"),
    ("qualifier", "Qualificador", "#9333EA", "ellipse"),
]

def find_col(df, key):
    for candidate in COLS.get(key, []):
        if candidate in df.columns:
            return candidate
    return None

def clean_value(value):
    if pd.isna(value):
        return ""
    value = str(value).strip()
    if value.lower() in {"nan", "none", "null"}:
        return ""
    return value

def short(text, limit=42):
    text = clean_value(text).replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"

def node_text(kind, value, row_num):
    prefix = {"claim": "Afirmação", "data": "Dado", "warrant": "Justificativa",
              "rebuttal": "Refutação", "backing": "Apoio", "qualifier": "Qualificador"}[kind]
    return f"{prefix} {row_num}"

def main():
    with st.sidebar:
        st.header("1. Carregar dados")
        uploaded = st.file_uploader("Envie sua planilha de anotações", type=["xlsx", "xls", "csv"])
        st.caption("A planilha deve ter uma linha por anotação e colunas que identifiquem os elementos de Toulmin.")
        st.divider()
        st.header("2. Explorar")
        st.caption("Os filtros aparecem depois que um arquivo válido é carregado.")

    if uploaded is None:
        st.info("Comece enviando uma planilha Excel (.xlsx/.xls) ou CSV.")
        st.markdown("### O que você poderá fazer")
        c1, c2, c3 = st.columns(3)
        c1.markdown("**Filtrar conversas**\n\nEscolha uma ou várias conversas para reduzir a rede.")
        c2.markdown("**Inspecionar argumentos**\n\nSelecione uma afirmação e consulte os trechos e justificativas originais.")
        c3.markdown("**Exportar uma seleção**\n\nBaixe as linhas filtradas para continuar sua análise.")
        with st.expander("Formato esperado"):
            st.write("Colunas principais: `Conversation_id`, `Texto`, e os trechos extraídos de claim, dado, warrant, rebuttal, backing e qualifier.")
            st.write("O aplicativo também aceita os cabeçalhos completos do seu modelo de anotação.")
        return

    try:
        if uploaded.name.lower().endswith(".csv"):
            try:
                df = pd.read_csv(uploaded)
            except UnicodeDecodeError:
                uploaded.seek(0)
                df = pd.read_csv(uploaded, encoding="latin-1")
        else:
            df = pd.read_excel(uploaded)
    except Exception as exc:
        st.error(f"Não foi possível ler o arquivo: {exc}")
        return

    if df.empty:
        st.warning("O arquivo não contém linhas.")
        return

    conv_col = find_col(df, "conversation")
    claim_col = find_col(df, "claim")
    if claim_col is None:
        st.error("Não encontrei a coluna do trecho de afirmação (claim). Confira o cabeçalho da planilha.")
        with st.expander("Colunas detectadas"):
            st.write(list(df.columns))
        return

    # Sidebar filters
    with st.sidebar:
        st.header("Filtros de exploração")
        if conv_col:
            conv_values = df[conv_col].dropna().astype(str).unique().tolist()
            conv_values = sorted(conv_values)
            selected_convs = st.multiselect(
                "Conversas",
                options=conv_values,
                default=conv_values[:3] if len(conv_values) > 3 else conv_values,
                help="Deixe selecionadas apenas as conversas que deseja explorar."
            )
            if selected_convs:
                filtered = df[df[conv_col].astype(str).isin(selected_convs)].copy()
            else:
                filtered = df.iloc[0:0].copy()
        else:
            filtered = df.copy()
            st.warning("A coluna Conversation_id não foi encontrada; o filtro por conversa está desativado.")

        query = st.text_input("Buscar texto", placeholder="Digite uma palavra ou expressão…")
        if query:
            search_cols = [c for c in [claim_col, find_col(df, "text"), find_col(df, "data"),
                                       find_col(df, "warrant"), find_col(df, "rebuttal")] if c]
            mask = pd.Series(False, index=filtered.index)
            for col in search_cols:
                mask = mask | filtered[col].fillna("").astype(str).str.contains(query, case=False, regex=False)
            filtered = filtered[mask]

        with st.expander("Opções de visualização"):
            max_rows = st.slider("Máximo de anotações no grafo", min_value=10, max_value=500,
                                 value=120, step=10)
            show_labels = st.checkbox("Mostrar rótulos dos nós", value=True)
            physics = st.checkbox("Permitir estabilização automática", value=True)

    if filtered.empty:
        st.warning("Nenhuma anotação corresponde aos filtros. Tente selecionar outras conversas ou remover a busca.")
        return

    # Metrics
    total_claims = filtered[claim_col].apply(clean_value).ne("").sum()
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Linhas filtradas", f"{len(filtered):,}")
    metric2.metric("Afirmações encontradas", f"{total_claims:,}")
    metric3.metric("Conversas selecionadas", filtered[conv_col].nunique() if conv_col else "—")
    element_count = sum(
        1 for key in ["data", "warrant", "rebuttal", "backing", "qualifier"]
        if find_col(df, key) is not None
    )
    metric4.metric("Tipos de elemento disponíveis", f"{element_count + 1}/6")

    if len(filtered) > max_rows:
        st.warning(f"A seleção contém {len(filtered)} linhas. Para manter a rede legível, o grafo mostra as primeiras {max_rows}; a tabela e a exportação continuam usando todos os resultados filtrados.")
        graph_df = filtered.head(max_rows)
    else:
        graph_df = filtered

    st.markdown("### Rede argumentativa")
    st.caption("Passe o cursor sobre um nó para ver o trecho completo. As ligações representam relações estruturais sugeridas pelo modelo de anotação, não uma validação automática da qualidade do argumento.")

    legend_items = []
    for key, label, color, shape in ELEMENTS:
        if find_col(df, key):
            legend_items.append((label, color))
    legend = st.columns(min(len(legend_items), 6) or 1)
    for i, (label, color) in enumerate(legend_items):
        with legend[i % len(legend)]:
            st.markdown(f"<span style='color:{color};font-size:1.15rem'>●</span> {html.escape(label)}", unsafe_allow_html=True)

    net = Network(height="590px", width="100%", bgcolor="#FFFFFF", font_color="#101828",
                  directed=True, cdn_resources="in_line")
    net.set_options("""
    {
      "nodes": {"font": {"size": 14, "face": "Arial"}, "borderWidth": 1,
                "shadow": {"enabled": true, "size": 4, "x": 1, "y": 2}},
      "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.55}},
                "color": {"color": "#D0D5DD", "highlight": "#667085"},
                "smooth": {"type": "dynamic"}, "font": {"size": 10, "align": "middle"}},
      "interaction": {"hover": true, "navigationButtons": true, "keyboard": true,
                      "multiselect": true},
      "physics": {"enabled": true, "stabilization": {"enabled": true, "iterations": 120},
                  "forceAtlas2Based": {"gravitationalConstant": -45, "centralGravity": 0.008,
                                       "springLength": 130, "springConstant": 0.08,
                                       "damping": 0.4},
                  "solver": "forceAtlas2Based"}
    }
    """)
    if not physics:
        net.toggle_physics(False)

    type_cols = {key: find_col(df, key) for key, *_ in ELEMENTS}
    text_col = find_col(df, "text")
    id_col = find_col(df, "id")
    reason_keys = {
        "claim": "claim_reason", "data": "data_reason", "warrant": "warrant_reason",
        "rebuttal": "rebuttal_reason", "backing": "backing_reason", "qualifier": "qualifier_reason"
    }
    added_nodes = set()
    claim_options = []
    claim_rows = {}

    for row_index, row in graph_df.iterrows():
        row_label = clean_value(row[id_col]) if id_col else str(row_index + 1)
        row_label = row_label or str(row_index + 1)
        values = {key: clean_value(row[col]) if col else "" for key, col in type_cols.items()}
        claim_value = values["claim"]
        if not claim_value:
            continue

        claim_id = f"claim::{row_index}"
        claim_label = short(claim_value, 38) if show_labels else f"Afirmação {row_label}"
        claim_title = f"<b>Afirmação (claim)</b><br>{html.escape(claim_value)}"
        if text_col and clean_value(row[text_col]):
            claim_title += f"<br><br><b>Texto original</b><br>{html.escape(clean_value(row[text_col]))}"
        net.add_node(claim_id, label=claim_label, title=claim_title, color="#FEE4E2",
                     font={"color": "#912018"}, shape="box", borderWidth=2, size=24)
        added_nodes.add(claim_id)

        row_node_ids = {"claim": claim_id}
        for kind, label, color, shape in ELEMENTS[1:]:
            value = values[kind]
            if not value:
                continue
            node_id = f"{kind}::{row_index}"
            node_label = short(value, 31) if show_labels else label
            reason_col = find_col(df, reason_keys[kind])
            reason = clean_value(row[reason_col]) if reason_col else ""
            title = f"<b>{html.escape(label)}</b><br>{html.escape(value)}"
            if reason:
                title += f"<br><br><b>Justificativa da anotação</b><br>{html.escape(reason)}"
            net.add_node(node_id, label=node_label, title=title, color=color, shape=shape, size=18)
            added_nodes.add(node_id)
            row_node_ids[kind] = node_id

            # Explicitly label the relation; do not imply cross-row links not present in the sheet.
            relation = {
                "data": "dá suporte a",
                "warrant": "justifica",
                "rebuttal": "contesta",
                "backing": "dá apoio a",
                "qualifier": "qualifica"
            }[kind]
            edge_color = "#D97706" if kind == "rebuttal" else "#98A2B3"
            net.add_edge(node_id, claim_id, label=relation, title=relation, color=edge_color,
                         arrows="to")

        claim_options.append(f"{row_label} — {short(claim_value, 90)}")
        claim_rows[claim_options[-1]] = (row_index, row)

    if len(added_nodes) == 0:
        st.info("Não há afirmações com texto nas linhas filtradas.")
    else:
        try:
            html_graph = net.generate_html()
            components.html(html_graph, height=620, scrolling=False)
        except Exception as exc:
            st.error(f"Não foi possível renderizar a rede: {exc}")

    st.markdown("### Inspecionar uma afirmação")
    if claim_options:
        selected_claim = st.selectbox("Escolha uma afirmação para ver os detalhes", claim_options)
        row_index, row = claim_rows[selected_claim]
        a, b = st.columns([1.15, 1])
        with a:
            st.markdown("**Texto original da publicação**")
            original = clean_value(row[text_col]) if text_col else ""
            st.write(original or "Não preenchido na planilha.")
            st.markdown("**Afirmação (claim)**")
            st.write(clean_value(row[claim_col]) or "Não preenchida.")
            if conv_col:
                st.caption(f"Conversation_id: {clean_value(row[conv_col]) or 'não informado'}")
            if id_col:
                st.caption(f"ID da anotação: {clean_value(row[id_col]) or 'não informado'}")
        with b:
            for key, label, _, _ in ELEMENTS[1:]:
                col = type_cols[key]
                value = clean_value(row[col]) if col else ""
                if value:
                    with st.expander(label, expanded=(key == "rebuttal")):
                        st.write(value)
                        reason_col = find_col(df, reason_keys[key])
                        reason = clean_value(row[reason_col]) if reason_col else ""
                        if reason:
                            st.caption("Justificativa da anotação")
                            st.write(reason)
                        present_col = find_col(df, f"{key}_present")
                        if present_col:
                            st.caption(f"Presente na anotação: {clean_value(row[present_col]) or 'não informado'}")

    st.markdown("### Dados filtrados")
    with st.expander("Abrir tabela de anotações", expanded=False):
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Baixar seleção filtrada em CSV", data=csv_bytes,
                       file_name="heiwa_anotacoes_filtradas.csv", mime="text/csv")

    with st.expander("Sobre a leitura do grafo"):
        st.write("Cada linha com claim gera um nó de afirmação. Elementos extraídos da mesma linha são ligados a essa afirmação. Esta versão não deduplica textos iguais nem identifica automaticamente quando uma afirmação de uma linha refuta outra afirmação de outra linha. Essas relações exigem uma anotação explícita ou uma etapa de análise adicional.")

main()
