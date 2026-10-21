import streamlit as st
import pandas as pd
from pyvis.network import Network
import streamlit.components.v1 as components

# Configuração da página
st.set_page_config(page_title="Heiwa Graph Visualizer", layout="wide")
st.title("HEIWA - Mapeamento de Argumentos de Toulmin")

# Upload direto na interface (simplifica para leigos)
uploaded_file = st.file_uploader("Arraste a planilha de anotações (.xlsx) aqui", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner("Processando topologia dos argumentos..."):
        # Processamento em memória
        df = pd.read_excel(uploaded_file)
        
        # Instancia o grafo PyVis
        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
        
        # Lógica de extração e plotagem
        for index, row in df.iterrows():
            claim = row.get('Trecho que contém a afirmação (claim) extraída')
            data = row.get('Trecho que contém dados extraídos')
            
            # Se não tem claim, não há nó central para desenhar
            if pd.isna(claim):
                continue
                
            claim_id = f"claim_{index}"
            # Renderiza o nó de Afirmação
            net.add_node(claim_id, label="Afirmação", title=str(claim), color="#ff4b4b")
            
            # Se houver dados/evidências, cria o nó e a aresta conectando à afirmação
            if not pd.isna(data):
                data_id = f"data_{index}"
                net.add_node(data_id, label="Dado", title=str(data), color="#4b4bff")
                net.add_edge(data_id, claim_id, title="Baseia-se em")
                
        # Gera o HTML temporário e exibe dentro do Streamlit
        net.save_graph("grafo_temp.html")
        HtmlFile = open("grafo_temp.html", 'r', encoding='utf-8')
        components.html(HtmlFile.read(), height=620)