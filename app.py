import streamlit as st
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components

st.set_page_config(page_title="Heiwa Graph Visualizer", layout="wide")
st.title("HEIWA - Mapeamento de Argumentos de Toulmin")

uploaded_file = st.file_uploader("Arraste a planilha de anotações (.xlsx) aqui", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    
    # 1. Criação da Barra Lateral de Filtros
    st.sidebar.header("Filtros de Exploração")
    conv_ids = df['Conversation_id'].dropna().astype(str).unique().tolist()
    # Carrega apenas as 3 primeiras conversas por padrão para evitar poluição visual
    selected_conv = st.sidebar.multiselect("Selecione os IDs das Conversas:", conv_ids, default=conv_ids[:3])
    
    df_filtered = df[df['Conversation_id'].astype(str).isin(selected_conv)]
    
    # 2. Configuração Avançada da Rede (Menus interativos e física)
    net = Network(height="650px", width="100%", bgcolor="#ffffff", font_color="black", select_menu=True)
    net.force_atlas_2based() # Algoritmo de física melhor para grafos de argumentação
    
    for index, row in df_filtered.iterrows():
        claim = row.get('Trecho que contém a afirmação (claim) extraída')
        data = row.get('Trecho que contém dados extraídos')
        warrant = row.get('Trecho que contém justificativa (warrant) extraído')
        rebuttal = row.get('Trecho que contém refutação (rebuttal) extraído')
        
        if pd.isna(claim):
            continue
            
        claim_id = f"claim_{index}"
        
        # Nó Central: Afirmação (Formato de caixa, cor forte)
        net.add_node(claim_id, label=f"Claim {index}", title=str(claim), color="#E50914", shape="box")
        
        # Nó Periférico: Dados
        if not pd.isna(data):
            data_id = f"data_{index}"
            net.add_node(data_id, label="Dado", title=str(data), color="#4b4bff", size=15)
            net.add_edge(data_id, claim_id, title="Baseia-se em", color="#a3a3a3")
            
        # Nó Periférico: Justificativa (Warrant)
        if not pd.isna(warrant):
            warrant_id = f"warrant_{index}"
            net.add_node(warrant_id, label="Justificativa", title=str(warrant), color="#28a745", size=15)
            net.add_edge(warrant_id, claim_id, title="Justifica", color="#a3a3a3")
            
        # Nó Periférico: Refutação (Rebuttal)
        if not pd.isna(rebuttal):
            rebuttal_id = f"rebuttal_{index}"
            net.add_node(rebuttal_id, label="Refutação", title=str(rebuttal), color="#ffc107", shape="triangle", size=20)
            net.add_edge(rebuttal_id, claim_id, title="Refuta", color="#ffc107")

    # 3. Adiciona painel para o usuário manipular a física do grafo
    net.show_buttons(filter_=['physics'])
    
    net.save_graph("grafo_avancado.html")
    HtmlFile = open("grafo_avancado.html", 'r', encoding='utf-8')
    components.html(HtmlFile.read(), height=850)