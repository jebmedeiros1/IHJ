import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
from sqlalchemy import text
from streamlit_authenticator.authenticate import Authenticate
import yaml
from yaml.loader import SafeLoader

with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Criando o autenticador
authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Verifica se o usuário está autenticado
if not st.session_state.get("authentication_status"):
    st.warning("Você precisa estar logado para acessar esta página.")
    st.stop()

# --- Configuração do banco de dados (PostgreSQL) ---------------------------
# Host do container Docker
host = "postgres"          # ou o nome do serviço se estiver no mesmo docker-compose
port = 5432                    # 5432 é o padrão; ajuste se mapeou outra porta
database = "ihj_database"      # nome do banco
username = "user"          # usuário do PostgreSQL
password = "pass"        # senha do PostgreSQL

# IMPORTANTE: instale o driver do PostgreSQL:
#   pip install psycopg2-binary
# -------------------------------------------------------------------------

# Cria a engine SQLAlchemy para PostgreSQL
engine = create_engine(
    f"postgresql+psycopg2://{username}:{quote_plus(password)}@{host}:{port}/{database}",
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,                 # True se quiser ver as queries no console
    connect_args={              # opcional — define o search_path
        "options": "-c search_path=dbo"
    }
)


def sql(_query):
    with engine.connect() as connection:
       df = pd.read_sql(text(_query), connection)
    return df

# Função para calcular similaridade
def calculate_similarity(df, target_equipment):
    target_row = df[df['equipamento'] == target_equipment]
    
    if target_row.empty:
        return None, None
    
    target_row_data = target_row.drop(columns=['equipamento']).iloc[0]
    aligned_df = df.drop(columns=['equipamento']).reindex(columns=target_row_data.index)
    
    comparison = aligned_df.apply(lambda row: row == target_row_data, axis=1)
    similarity_score = comparison.sum(axis=1)
    
    if 'PMM_GRUPO' in df.columns:
        df['Similarity_Score'] = similarity_score
        grupo_alvo = target_row['PMM_GRUPO'].values[0]
        df.loc[df['PMM_GRUPO'] == grupo_alvo, 'Similarity_Score'] = 99
        
    elif 'PME_GRUPO' in df.columns:
        df['Similarity_Score'] = similarity_score
        grupo_alvo = target_row['PME_GRUPO'].values[0]
        df.loc[df['PME_GRUPO'] == grupo_alvo, 'Similarity_Score'] = 99
    else:
        df['Similarity_Score'] = similarity_score
    
    similar_options = df[df['equipamento'] != target_equipment].sort_values(by='Similarity_Score', ascending=False)
    return similar_options, target_row

# Função para destacar diferenças após transposição, ignorando a primeira e última linha na formatação
def highlight_differences(transposed_view):
    target_values = transposed_view.iloc[:, 0]  # Primeira coluna como referência

    def highlight_row(row):
        # Pula 1ª e últimas 3 linhas
        if row.name in transposed_view.index[[0, -2, -3,-4]]:
            return [''] * len(transposed_view.columns)
        
        return [
            'background-color: red; color: white;' 
            if col != "equipamento" and row[col] != row[target_values.name] 
            else ''  
            for col in transposed_view.columns
        ]

    # Aplica o estilo sem remover as linhas
    return transposed_view.style.apply(highlight_row, axis=1)

# Configuração do app Streamlit


# 1. Lê o arquivo .txt com separador de tabulação
df_info = pd.read_csv('equip_s4.txt', sep='\t', encoding='latin1', usecols=['Equipam.', 'Loc.instalação','Denominação do loc.instalação', 'Material'])
#df_info = df_info[['Equipam.', 'Loc.instalação','Denominação do loc.instalação', 'Material']]

st.header("🔍 Análise de equipamentos Semelhantes.")
col1, col2 = st.columns([0.25, 0.75])


col1.subheader("Selecione o equipamento alvo:")
target_equipment = col1.text_input("Digite o código do equipamento", placeholder='Ex. Motor001').upper()
qtd = col1.number_input("Insira o número de registros", value=10)
if col1.button("Buscar equipamento"):
    query =f"SELECT * FROM TB_Caract  WHERE equipamento = '{target_equipment}'"
    df_caract = sql(query)
    #_df_pivot = df_caract.pivot_table(index='id_caracteristica', columns=['equipamento', 'centro', 'classe'], values='valor', aggfunc='first')
    #_df_pivot

    with col2:
        with st.spinner("Carregando..."):
            query=f"SELECT * FROM TB_Caract WHERE classe IN (SELECT classe FROM TB_Caract WHERE equipamento = '{target_equipment}')"
            _df_global=sql(query)
            #_df_global2= _df_global.pivot_table(index='id_caracteristica', columns=['equipamento', 'centro', 'classe'], values='valor', aggfunc='first')
            _df_global= _df_global.pivot_table(index=['equipamento','centro', 'classe'], columns='id_caracteristica', values='valor', aggfunc='first')
            df_reset = _df_global.reset_index()
            similar_options, target_row = calculate_similarity(df_reset, target_equipment)
            
            if similar_options is not None: 
                st.subheader(f"🔗 {qtd} equipamentos semelhantes:")
                
                top_similares = similar_options[['equipamento', 'Similarity_Score']].head(qtd)
                #st.write(top_similares)
                
                #if st.button("Mostrar detalhes completos"):
                #st.subheader('Detalhes dos equipamentos:')
                target_row['Similarity_Score'] = 'Similaridade'
                detailed_view = pd.concat([target_row, similar_options.head(qtd)])
                      
                equip_usados = detailed_view['equipamento'].unique()
                
                df_info_filtrado = df_info[df_info['Equipam.'].isin(equip_usados)]
                df_merged = detailed_view.merge(df_info, left_on='equipamento', right_on='Equipam.', how='left')
                df_merged = df_merged.drop(columns=['Equipam.'])
                
                styled_transposed_view = highlight_differences(df_merged.T)
                st.write(styled_transposed_view)
            else:
                st.error('equipamento alvo não encontrado na base de dados.')

