import streamlit as st
import database as db
import utils

def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'selecting_user' not in st.session_state:
        st.session_state.selecting_user = None
    if 'creating_account' not in st.session_state:
        st.session_state.creating_account = False

def login(username, password):
    user_data = db.get_user(username)
    # user_data = (id, username, password, role, avatar_url)
    if user_data and user_data[2] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = username
        st.session_state.selecting_user = None
        return True
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.selecting_user = None
    st.session_state.creating_account = False

def check_url_login():
    # Verifica se alguém clicou num avatar (que passou o nome pela URL)
    if "user" in st.query_params:
        clicked_user = st.query_params["user"]
        
        if clicked_user == "__NEW__":
            # Clicou no botão de criar nova conta
            st.session_state.creating_account = True
            st.session_state.selecting_user = None
        else:
            # Clicou num utilizador existente
            all_users = [u[0] for u in db.get_all_users()]
            if clicked_user in all_users:
                st.session_state.selecting_user = clicked_user
                st.session_state.creating_account = False
        
        # Limpa a URL para não ficar presa e recarrega a página
        del st.query_params["user"]
        st.rerun()

def render_login_screen():
    # 1. Verifica os cliques na URL antes de desenhar qualquer coisa
    check_url_login()

    st.write("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #4F8BF9;'>Quem está acessando?</h1>", unsafe_allow_html=True)
    st.write("<br><br>", unsafe_allow_html=True)

    # 2. ECRÃ DE REGISTO (NOVA CONTA)
    if st.session_state.creating_account:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                st.subheader("➕ Criar Novo Perfil")
                with st.form("register_form"):
                    new_user = st.text_input("Nome de Utilizador")
                    new_pass = st.text_input("Palavra-passe", type="password")
                    new_role = st.selectbox("Cargo / Equipa", ["Engenharia/Dev", "Frontend", "Backend", "Design", "Negócios", "Infraestrutura", "Administrador"])
                    submit_reg = st.form_submit_button("Criar Conta", type="primary", use_container_width=True)
                    
                    if submit_reg:
                        if new_user and new_pass:
                            avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={new_user}&backgroundColor=c0aede"
                            if db.add_user(new_user, new_pass, new_role, avatar):
                                st.success("✅ Perfil criado com sucesso!")
                                st.session_state.creating_account = False
                                st.rerun()
                            else:
                                st.error("⚠️ Este nome já existe.")
                        else:
                            st.error("Por favor, preencha todos os campos.")
            
            if st.button("⬅️ Voltar aos perfis", use_container_width=True):
                st.session_state.creating_account = False
                st.rerun()

    # 3. ECRÃ DA PALAVRA-PASSE (PERFIL SELECIONADO)
    elif st.session_state.selecting_user:
        user_name = st.session_state.selecting_user
        user_data = db.get_user(user_name)
        avatar_url = utils.get_image_base64(user_data[4]) if user_data else "https://api.dicebear.com/7.x/avataaars/svg?seed=Generico"
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"<div style='text-align: center;'><img src='{avatar_url}' class='avatar-img' style='width: 180px; height: 180px; border-radius: 50%; object-fit: cover;'></div>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center;'>Olá, {user_name}!</h2>", unsafe_allow_html=True)
            st.write("<br>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                senha = st.text_input("Digite sua senha", type="password", autofocus=True)
                st.write("<br>", unsafe_allow_html=True)
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.form_submit_button("⬅️ Voltar", use_container_width=True):
                        st.session_state.selecting_user = None
                        st.rerun()
                with col_btn2:
                    if st.form_submit_button("Entrar ➡️", use_container_width=True):
                        if login(user_name, senha):
                            st.rerun()
                        else:
                            st.error("Senha incorreta!")

    # 4. GRELHA DE PERFIS (ECRÃ PRINCIPAL)
    else:
        # Vai buscar todos ao Supabase
        users = db.get_all_users()
        
        # Cria a lista de cartões (Utilizadores + Botão de Novo)
        cards = [{"name": u[0], "avatar": utils.get_image_base64(u[2]), "id": u[0]} for u in users]
        cards.append({"name": "Novo Perfil", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=%2B&backgroundColor=e0e0e0", "id": "__NEW__"})

        cols_per_row = 5
        
        for i in range(0, len(cards), cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < len(cards):
                    card = cards[i + j]
                    with cols[j]:
                        # O truque do HTML com a href nativa
                        html_card = f"""
                        <a href="?user={card['id']}" target="_self" class="profile-link" style="text-decoration: none; color: inherit;">
                            <div class="avatar-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; transition: transform 0.2s;">
                                <img src="{card['avatar']}" class="avatar-img" style="width: 140px; height: 140px; border-radius: 50%; object-fit: cover; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                                <div class="avatar-name" style="margin-top: 15px; font-weight: bold; font-size: 1.2rem;">{card['name']}</div>
                            </div>
                        </a>
                        """
                        st.markdown(html_card, unsafe_allow_html=True)
