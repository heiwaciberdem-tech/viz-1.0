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

# Atualizado com os links das imagens (Shape configurado como 'image')
ELEMENTS = [
    ("claim", "Afirmação (claim)", "#D92D20", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/afir-removebg-preview.png"),
    ("data", "Dado", "#4F46E5", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/dado-removebg-preview.png"),
    ("warrant", "Justificativa (warrant)", "#16A34A", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/download.png"),
    ("rebuttal", "Refutação (rebuttal)", "#D97706", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/refut-removebg-preview.png"),
    ("backing", "Apoio adicional (backing)", "#0891B2", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/download%20(1).png"),
    ("qualifier", "Qualificador", "#9333EA", "image", "https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/Gemini_Generated_Image_9mm63g9mm63g9mm6-removebg-preview%20(1).png"),
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

def main():
    with st.sidebar:
        st.header("1. Carregar dados")
        uploaded = st.file_uploader("Envie a sua folha de cálculo", type=["xlsx", "xls", "csv"])
        st.caption("A folha deve ter uma linha por anotação e colunas que identifiquem os elementos de Toulmin.")
        st.divider()
        st.header("2. Explorar")
        st.caption("Os filtros aparecem depois que um ficheiro válido é carregado.")

    if uploaded is None:
        st.info("Comece por enviar um ficheiro Excel (.xlsx/.xls) ou CSV.")
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
        st.error(f"Não foi possível ler o ficheiro: {exc}")
        return

    if df.empty:
        st.warning("O ficheiro não contém linhas.")
        return

    conv_col = find_col(df, "conversation")
    claim_col = find_col(df, "claim")
    if claim_col is None:
        st.error("Não encontrei a coluna do trecho de afirmação (claim). Confira o cabeçalho.")
        return

    with st.sidebar:
        st.header("Filtros de exploração")
        
        # Filtro primário alterado de ID para Claim
        claim_values = df[claim_col].dropna().unique().tolist()
        selected_claims = st.multiselect(
            "Afirmações (Claims)",
            options=claim_values,
            default=claim_values[:3] if len(claim_values) > 3 else claim_values,
            format_func=lambda x: short(x, 60), # Trunca visualmente para não quebrar o layout
            help="Selecione as afirmações que atuarão como nós centrais da visualização."
        )
        
        if selected_claims:
            filtered = df[df[claim_col].isin(selected_claims)].copy()
        else:
            filtered = df.iloc[0:0].copy()

        query = st.text_input("Buscar texto geral", placeholder="Digite uma palavra ou expressão…")
        if query:
            search_cols = [c for c in [claim_col, find_col(df, "text"), find_col(df, "data"),
                                       find_col(df, "warrant"), find_col(df, "rebuttal")] if c]
            mask = pd.Series(False, index=filtered.index)
            for col in search_cols:
                mask = mask | filtered[col].fillna("").astype(str).str.contains(query, case=False, regex=False)
            filtered = filtered[mask]

        st.divider()
        st.subheader("Elementos Obrigatórios (AND)")
        req_elements = st.multiselect(
            "Mostrar apenas anotações que contenham:",
            options=["Dado", "Justificativa", "Refutação", "Apoio", "Qualificador"],
            help="O grafo renderizará exclusivamente as linhas que possuam a interseção exata de TODOS os elementos."
        )
        
        if req_elements:
            if "Dado" in req_elements and find_col(df, "data"):
                filtered = filtered[filtered[find_col(df, "data")].apply(clean_value) != ""]
            if "Justificativa" in req_elements and find_col(df, "warrant"):
                filtered = filtered[filtered[find_col(df, "warrant")].apply(clean_value) != ""]
            if "Refutação" in req_elements and find_col(df, "rebuttal"):
                filtered = filtered[filtered[find_col(df, "rebuttal")].apply(clean_value) != ""]
            if "Apoio" in req_elements and find_col(df, "backing"):
                filtered = filtered[filtered[find_col(df, "backing")].apply(clean_value) != ""]
            if "Qualificador" in req_elements and find_col(df, "qualifier"):
                filtered = filtered[filtered[find_col(df, "qualifier")].apply(clean_value) != ""]

        with st.expander("Opções de visualização"):
            max_rows = st.slider("Máximo de anotações no grafo", 10, 500, 120, 10)
            show_labels = st.checkbox("Mostrar rótulos dos nós", value=True)
            physics = st.checkbox("Permitir estabilização automática", value=True)

    if filtered.empty:
        st.warning("Nenhuma anotação corresponde aos filtros restritivos. Altere a seleção.")
        return

    total_claims = filtered[claim_col].apply(clean_value).ne("").sum()
    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Linhas filtradas", f"{len(filtered):,}")
    metric2.metric("Afirmações analisadas", f"{total_claims:,}")
    metric3.metric("Conversas relacionadas", filtered[conv_col].nunique() if conv_col else "—")
    metric4.metric("Nós renderizados (Max)", min(len(filtered), max_rows))

    if len(filtered) > max_rows:
        graph_df = filtered.head(max_rows)
    else:
        graph_df = filtered

    st.markdown("### Rede Argumentativa Interativa")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("🧠 Entenda o Modelo de Toulmin", expanded=False):
            st.markdown("""
            Esta visualização mapeia debates utilizando o **Modelo de Toulmin**, desconstruindo argumentos em componentes lógicos:
            * **Afirmação (Claim):** A tese central que está a ser defendida.
            * **Dado (Data):** Os fatos ou evidências que servem de base.
            * **Justificativa (Warrant):** A premissa lógica que conecta o Dado à Afirmação.
            * **Apoio (Backing):** Conhecimento adicional que valida a Justificativa.
            * **Refutação (Rebuttal):** Objeções ou exceções que limitam a Afirmação.
            * **Qualificador (Qualifier):** Expressa o grau de certeza (ex: "provavelmente").
            """)
    with col2:
        with st.expander("🖱️ Como interagir com o grafo", expanded=False):
            st.markdown("""
            * **Zoom e Pan:** Use a roda do rato para aproximar/afastar. Clique no fundo e arraste para mover a câmara.
            * **Inspecionar:** Posicione o cursor sobre qualquer nó para ler o texto original e a justificativa da anotação.
            * **Reorganizar:** Clique e arraste um nó para alterar o layout. A física do sistema reajustará as ligações automaticamente.
            * **Foco:** Clique num nó específico para escurecer o resto da rede e focar apenas nas suas conexões diretas.
            """)

    LEGEND_HTML = """
    <style>
    .legend-container { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; background: #0E1117; padding: 16px; border-radius: 12px; }
    .legend-card { display: flex; align-items: center; justify-content: space-between; padding-bottom: 12px; border-bottom: 1px solid #1F2937; }
    .legend-card:last-child { border-bottom: none; padding-bottom: 0; }
    .legend-icon-text { display: flex; align-items: center; gap: 16px; }
    .legend-icon { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
    .legend-icon img { width: 100%; height: 100%; object-fit: contain; }
    .legend-title { color: #F9FAFB; font-weight: 600; font-size: 0.95rem; margin: 0; }
    .legend-desc { color: #9CA3AF; font-size: 0.85rem; margin: 0; }
    .badge { font-size: 0.75rem; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    </style>
    <div class="legend-container">
        <div class="legend-card">
            <div class="legend-icon-text">
                <div class="legend-icon"><img src="https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/afir-removebg-preview.png"></div>
                <div><p class="legend-title">Afirmação (Claim)</p><p class="legend-desc">A posição defendida no argumento.</p></div>
            </div>
            <span class="badge" style="color: #D92D20; background: rgba(217, 45, 32, 0.1);">Vermelho</span>
        </div>
        <div class="legend-card">
            <div class="legend-icon-text">
                <div class="legend-icon"><img src="https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/dado-removebg-preview.png"></div>
                <div><p class="legend-title">Dado</p><p class="legend-desc">A evidência ou informação que sustenta a afirmação.</p></div>
            </div>
            <span class="badge" style="color: #4F46E5; background: rgba(79, 70, 229, 0.1);">Azul</span>
        </div>
        <div class="legend-card">
            <div class="legend-icon-text">
                <div class="legend-icon"><img src="https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/download.png"></div>
                <div><p class="legend-title">Justificativa (Warrant)</p><p class="legend-desc">A lógica que conecta o dado à afirmação.</p></div>
            </div>
            <span class="badge" style="color: #059669; background: rgba(5, 150, 105, 0.1);">Verde</span>
        </div>
        <div class="legend-card">
            <div class="legend-icon-text">
                <div class="legend-icon"><img src="https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/refut-removebg-preview.png"></div>
                <div><p class="legend-title">Refutação (Rebuttal)</p><p class="legend-desc">Uma condição ou objeção que desafia a afirmação.</p></div>
            </div>
            <span class="badge" style="color: #D97706; background: rgba(217, 119, 6, 0.1);">Âmbar</span>
        </div>
        <div class="legend-card">
            <div class="legend-icon-text">
                <div class="legend-icon"><img src="https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/%C3%ADcones/download%20(1).png"></div>
                <div><p class="legend-title">Apoio adicional (Backing)</p><p class="legend-desc">O fundamento que reforça a justificativa.</p></div>
            </div>
            <span class="badge" style="color: #0891B2; background: rgba(8, 145, 178, 0.1);">Ciano</span>
        </div>
        <div class="legend-card">
            <div class="legend-icon-text">
                <div class="legend-icon"><img src="https://ik.imagekit.io/csktgzt59/Heiwa%20IMG/New%20Folder/Gemini_Generated_Image_9mm63g9mm63g9mm6.jpg"></div>
                <div><p class="legend-title">Qualificador (Qualifier)</p><p class="legend-desc">O grau de certeza ou força da afirmação.</p></div>
            </div>
            <span class="badge" style="color: #9333EA; background: rgba(147, 51, 234, 0.1);">Roxo</span>
        </div>
    </div>
    """   
    st.markdown(LEGEND_HTML, unsafe_allow_html=True)

    net = Network(height="590px", width="100%", bgcolor="#FFFFFF", font_color="#101828",
                  directed=True, cdn_resources="remote")
    net.set_options("""
    {
      "nodes": {"font": {"size": 14, "face": "Arial"}},
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
        claim_label = short(claim_value, 38) if show_labels else ""
        
        # Correção do tooltip: texto simples com quebras de linha (\n)
        claim_title = f"Afirmação (claim):\n{claim_value}"
        if text_col and clean_value(row[text_col]):
            claim_title += f"\n\nTexto original:\n{clean_value(row[text_col])}"
            
        _, _, _, shape, img_url = ELEMENTS[0]
        net.add_node(claim_id, label=claim_label, title=claim_title, shape=shape, image=img_url, size=35)
        added_nodes.add(claim_id)

        for kind, label, color, shape, img_url in ELEMENTS[1:]:
            value = values[kind]
            if not value:
                continue
            node_id = f"{kind}::{row_index}"
            node_label = short(value, 31) if show_labels else ""
            reason_col = find_col(df, reason_keys[kind])
            reason = clean_value(row[reason_col]) if reason_col else ""
            
            # Correção do tooltip para os nós periféricos
            title = f"{label}:\n{value}"
            if reason:
                title += f"\n\nJustificativa da anotação:\n{reason}"
                
            if img_url:
                net.add_node(node_id, label=node_label, title=title, shape="image", image=img_url, size=25)
            else:
                net.add_node(node_id, label=node_label, title=title, color=color, shape=shape, size=20)
                
            added_nodes.add(node_id)

            relation = {
                "data": "dá suporte a",
                "warrant": "justifica",
                "rebuttal": "contesta",
                "backing": "dá apoio a",
                "qualifier": "qualifica"
            }[kind]
            edge_color = "#D97706" if kind == "rebuttal" else "#98A2B3"
            net.add_edge(node_id, claim_id, label=relation, title=relation, color=edge_color, arrows="to")

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
            st.write(original or "Não preenchido na folha.")
            st.markdown("**Afirmação (claim)**")
            st.write(clean_value(row[claim_col]) or "Não preenchida.")
            if conv_col:
                st.caption(f"Conversation_id: {clean_value(row[conv_col]) or 'não informado'}")
            if id_col:
                st.caption(f"ID da anotação: {clean_value(row[id_col]) or 'não informado'}")
        with b:
            for key, label, _, _, _ in ELEMENTS[1:]:
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

    st.markdown("### Dados filtrados")
    with st.expander("Abrir tabela de anotações", expanded=False):
        st.dataframe(filtered, use_container_width=True, hide_index=True)
    csv_bytes = filtered.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Baixar seleção filtrada em CSV", data=csv_bytes,
                       file_name="heiwa_anotacoes_filtradas.csv", mime="text/csv")

main()