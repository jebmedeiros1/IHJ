import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import yaml
from yaml.loader import SafeLoader
from streamlit_authenticator.authenticate import Authenticate


st.set_page_config(
    page_title="IHJ sistema de Busca de Equipamentos",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)
col1, col2,col3 = st.columns([0.30, 0.40,0.30])
col2.title(" 🔍 IHJ sistema de Busca de Equipamentos")



# Função para esconder a sidebar antes do login
def hide_sidebar():
    hide_streamlit_style = """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Modo desenvolvimento
_RELEASE = False

if not _RELEASE:
    
    # Carregando arquivo de configuração
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.load(file, Loader=SafeLoader)

    # Criando o autenticador
    authenticator = Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # Criando o widget de login
    try:
        with col2:
            authenticator.login()
    except Exception as e:
        st.error(e)

    # Esconder sidebar antes do login
    if not st.session_state.get('authentication_status'):
        hide_sidebar()

    # Se autenticado, mostra botões de navegação
    if st.session_state.get('authentication_status'):
        authenticator.logout()
        st.write(f'Bem Vindo(a) *{st.session_state["name"]}*')
        st.info("Utilize os botôes de navegação ao lado")

    elif st.session_state.get('authentication_status') is False:
        col2.error('Usuário ou senha incorretos')
    elif st.session_state.get('authentication_status') is None:
        col2.warning('Digite seu usuário e senha')
