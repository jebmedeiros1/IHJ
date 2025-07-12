import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
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

# Carregando o de/para classe
df_depara_classe = pd.read_csv('./classes.csv', dtype={'ID': str})
classe_dict = dict(zip(df_depara_classe['Nome'], df_depara_classe['ID']))
classe_reverse_dict = dict(zip(df_depara_classe['ID'], df_depara_classe['Nome']))

# Função para executar consultas SQL (com limpeza de cache)
@st.cache_data
def sql(_query):
    with engine.connect() as connection:
        return pd.read_sql(text(_query), connection)


# Função para limpar o cache antes de executar novas queries
def clear_cache_and_query(_query):
    st.cache_data.clear()  # Limpa o cache antes de buscar novos dados
    return sql(_query)


# Função para inserir equipamentos na tabela tb_temp
def lista_equip(_df):
    if _df.empty:
        return "Nenhum equipamento disponível para inserir."

    try:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM tb_temp"))
            _df.to_sql("tb_temp", con=engine, if_exists="append", index=False, method="multi")
        return "OK"
    except Exception as e:
        return f"Erro ao executar a inserção: {e}"


# Configuração do Streamlit
col1, col2,col3 = st.columns([0.80, 0.10,0.10])
col2.write(f'Bem Vindo(a) *{st.session_state["name"]}*') 
with col3:
    authenticator.logout()


st.header("🔍 Busca de equipamentos por Características")

# Estados iniciais
if "selected_classes" not in st.session_state:
    st.session_state["selected_classes"] = []
if "selected_values" not in st.session_state:
    st.session_state["selected_values"] = {}
if "unique_values_dict" not in st.session_state:
    st.session_state["unique_values_dict"] = {}

# Carrega classes disponíveis (com cache limpo)
with st.spinner("Carregando classes..."):
    try:
        df_classes = clear_cache_and_query('SELECT DISTINCT classe FROM tb_caract')
    except Exception as e:
        st.error(f"Erro ao carregar classes: {e}")
        st.stop()

# Pegando apenas as classes do banco que também estão no CSV
classes_validas = df_classes['classe'].dropna().astype(float).astype(int).astype(str).tolist()
nomes_validos = [classe_reverse_dict[c] for c in classes_validas if c in classe_reverse_dict]

st.sidebar.header("Seleção de classe")
selected_class_names = st.sidebar.multiselect("Escolha a(s) classe(s)", nomes_validos, default=[classe_reverse_dict[c] for c in st.session_state["selected_classes"] if c in classe_reverse_dict])

# Converter nomes de volta para IDs
selected_classes = [classe_dict[n] for n in selected_class_names]


if selected_classes != st.session_state["selected_classes"]:
    st.session_state["selected_classes"] = selected_classes
    st.session_state["selected_values"] = {}  # Limpa os filtros ao trocar a classe
    st.session_state["unique_values_dict"] = {}
    st.cache_data.clear()


# Se há classes selecionadas, carrega características correspondentes
if selected_classes:
    class_filter = ", ".join(selected_classes)  # Removendo aspas para números

    query = f"SELECT DISTINCT ds_caracteristica FROM tb_caract WHERE classe IN ({class_filter})"
    
    with st.spinner("Carregando características disponíveis..."):
        try:
            df_columns = clear_cache_and_query(query)
        except Exception as e:
            st.error(f"Erro ao carregar características: {e}")
            st.stop()

    if not df_columns.empty:
        filter_columns = df_columns['ds_caracteristica'].tolist()
        selected_filters = st.sidebar.multiselect("Escolha as colunas para filtrar", filter_columns, default=list(st.session_state["selected_values"].keys()))

        # Remover filtros que foram desmarcados
        for col in list(st.session_state["selected_values"].keys()):
            if col not in selected_filters:
                del st.session_state["selected_values"][col]

        if selected_filters:
            for column in selected_filters:
                if column not in st.session_state["unique_values_dict"]:
                    with st.spinner(f"Carregando valores para {column}..."):
                        df_values = clear_cache_and_query(
                            f"SELECT DISTINCT valor FROM tb_caract WHERE ds_caracteristica = '{column}' AND classe IN ({class_filter}) order by valor "
                        )
                        st.session_state["unique_values_dict"][column] = df_values['valor'].tolist()

            for column in selected_filters:
                st.session_state["selected_values"][column] = st.sidebar.multiselect(
                    f"Filtrar por {column}", 
                    st.session_state["unique_values_dict"][column], 
                    default=st.session_state["selected_values"].get(column, [])
                )

            if st.sidebar.button("Aplicar Filtros"):
                st.cache_data.clear()  # Limpa o cache ao aplicar filtros
                st.session_state["filtros_aplicados"] = True
            else:
                st.session_state["filtros_aplicados"] = False

# Aplicar filtros
if st.session_state.get("filtros_aplicados", False):
    with st.spinner("Aplicando filtros..."):
        filter_conditions = []
        conditions = []
        for col, values in st.session_state["selected_values"].items():
            for val in values:
                if val is None:
                    conditions.append("valor IS NULL")
                else:
                    conditions.append(f"valor = {repr(val)}")

            filter_conditions.append(
                f"EXISTS (SELECT 1 FROM tb_caract AS T2 "
                f"WHERE T2.equipamento = tb_caract.equipamento "
                f"AND ds_caracteristica = '{col}' "
                f"AND ({' OR '.join(conditions)}))"
            )
                    
            
          
        final_query = f"""
            SELECT DISTINCT equipamento 
            FROM tb_caract 
            WHERE classe IN ({class_filter}) 
            AND {' AND '.join(filter_conditions)}
        """
        
        try:
            filtered_df = clear_cache_and_query(final_query)
          
            if not filtered_df.empty:
                st.subheader("Tabela Filtrada")
                resultado = lista_equip(filtered_df)
                st.success(resultado)
                
                _query = "SELECT * FROM tb_caract WHERE equipamento IN (SELECT equipamento FROM tb_temp)"
                _df = clear_cache_and_query(_query)
                _df['valor'] = _df['valor'].fillna("None")
                if not _df.empty:
                    _df_pivot = _df.pivot_table(index='ds_caracteristica', columns=['equipamento', 'centro', 'classe'], values='valor', aggfunc='first')
                    st.dataframe(_df_pivot, use_container_width=True)
                else:
                    st.warning("Nenhum dado encontrado para os equipamentos filtrados.")
            else:
                st.warning("Nenhum equipamento encontrado com os filtros aplicados.")

        except Exception as e:
            st.error(f"Erro ao aplicar filtros: {e}")

    st.session_state["filtros_aplicados"] = False
else:
    st.sidebar.warning("Clique em 'Aplicar Filtros' para carregar os dados.")
