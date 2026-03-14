import streamlit as st
import database as db

def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None

def login(username, password):
    user_data = db.get_user(username)
    # user_data = (id, username, password, role, avatar_url)
    if user_data and user_data[2] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = username
        return True
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None

def render_login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #4F8BF9;'>Gestão de Projetos</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Faça login ou crie a sua conta para aceder ao Kanban.</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            tab_login, tab_register = st.tabs(["🔒 Entrar", "➕ Criar Conta"])
            
            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Nome de Utilizador")
                    password = st.text_input("Palavra-passe", type="password")
                    submit = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                    
                    if submit:
                        if login(username, password):
                            st.rerun()
                        else:
                            st.error("Utilizador ou palavra-passe incorretos.")
            
            with tab_register:
                with st.form("register_form"):
                    new_user = st.text_input("Novo Nome de Utilizador")
                    new_pass = st.text_input("Palavra-passe", type="password")
                    new_role = st.selectbox("Cargo / Equipa", ["Engenharia/Dev", "Frontend", "Backend", "Design", "Negócios", "Infraestrutura", "Administrador"])
                    submit_reg = st.form_submit_button("Criar Conta", use_container_width=True)
                    
                    if submit_reg:
                        if new_user and new_pass:
                            # Gera um avatar aleatório baseado no nome
                            avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={new_user}&backgroundColor=c0aede"
                            if db.add_user(new_user, new_pass, new_role, avatar):
                                st.success("✅ Conta criada com sucesso! Pode fazer login ao lado.")
                            else:
                                st.error("⚠️ Este nome de utilizador já existe.")
                        else:
                            st.error("Por favor, preencha todos os campos.")

def check_url_login():
    pass