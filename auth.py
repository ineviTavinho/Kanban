import streamlit as st
import database as db
import utils

def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    # Novas variáveis para controlar a navegação do estilo Disney+
    if 'selected_profile' not in st.session_state:
        st.session_state.selected_profile = None
    if 'creating_account' not in st.session_state:
        st.session_state.creating_account = False

def login(username, password):
    user_data = db.get_user(username)
    # user_data = (id, username, password, role, avatar_url)
    if user_data and user_data[2] == password:
        st.session_state.logged_in = True
        st.session_state.current_user = username
        st.session_state.selected_profile = None # Limpa a seleção para o próximo login
        return True
    return False

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.selected_profile = None
    st.session_state.creating_account = False

def render_login_screen():
    st.write("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #4F8BF9;'>Quem está a gerir projetos?</h1>", unsafe_allow_html=True)
    st.write("<br><br>", unsafe_allow_html=True)

    # 1. ECRÃ DE REGISTO (CRIAR CONTA)
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
                            # Gera o avatar inicial
                            avatar = f"https://api.dicebear.com/7.x/avataaars/svg?seed={new_user}&backgroundColor=c0aede"
                            if db.add_user(new_user, new_pass, new_role, avatar):
                                st.success("✅ Perfil criado com sucesso!")
                                st.session_state.creating_account = False # Volta para a grelha de perfis
                                st.rerun()
                            else:
                                st.error("⚠️ Este nome já existe.")
                        else:
                            st.error("Por favor, preencha todos os campos.")
            
            if st.button("⬅️ Voltar aos perfis", use_container_width=True):
                st.session_state.creating_account = False
                st.rerun()

    # 2. ECRÃ DE PALAVRA-PASSE (PERFIL SELECIONADO)
    elif st.session_state.selected_profile:
        col1, col2, col3 = st.columns([1, 1.5, 1])
        user = st.session_state.selected_profile
        user_data = db.get_user(user)
        avatar_url = user_data[4] if user_data else "https://api.dicebear.com/7.x/avataaars/svg?seed=Generico"
        avatar_b64 = utils.get_image_base64(avatar_url)
        
        with col2:
            with st.container(border=True):
                col_img, col_text = st.columns([1, 3])
                with col_img:
                    st.markdown(f"<img src='{avatar_b64}' style='width: 80px; height: 80px; border-radius: 50%; object-fit: cover;'>", unsafe_allow_html=True)
                with col_text:
                    st.subheader(f"Olá, {user}!")
                    st.caption("Insira a sua palavra-passe para aceder.")
                
                with st.form("pwd_form"):
                    pwd = st.text_input("Palavra-passe", type="password", autofocus=True)
                    submit_pwd = st.form_submit_button("Entrar", type="primary", use_container_width=True)
                    if submit_pwd:
                        if login(user, pwd):
                            st.rerun()
                        else:
                            st.error("❌ Palavra-passe incorreta!")
                            
            if st.button("⬅️ Escolher outro perfil", use_container_width=True):
                st.session_state.selected_profile = None
                st.rerun()

    # 3. ECRÃ INICIAL (GRELHA DE AVATARES - ESTILO DISNEY+)
    else:
        users = db.get_all_users()
        # Quantos cartões por linha? Vamos usar 4.
        cols_per_row = 4
        
        # Cria a lista de cartões combinando os utilizadores da BD + o botão de criar
        cards = [{"type": "user", "name": u[0], "avatar": utils.get_image_base64(u[2])} for u in users]
        cards.append({"type": "add", "name": "Novo Perfil", "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=%2B&backgroundColor=e0e0e0"})
        
        # Centraliza a grelha criando colunas vazias nas laterais
        col_space_left, col_center, col_space_right = st.columns([1, 4, 1])
        
        with col_center:
            # Desenha a grelha
            for i in range(0, len(cards), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(cards):
                        card = cards[i + j]
                        with cols[j]:
                            # Renderiza o Avatar Circular com efeito Hover
                            st.markdown(
                                f"""
                                <div style='text-align: center;'>
                                    <img src='{card["avatar"]}' 
                                         style='width: 120px; height: 120px; border-radius: 50%; object-fit: cover; 
                                                box-shadow: 0 4px 8px rgba(0,0,0,0.2); margin-bottom: 10px; 
                                                border: 3px solid transparent; transition: 0.3s;' 
                                         onmouseover='this.style.borderColor=\"#4F8BF9\"; this.style.transform=\"scale(1.05)\";' 
                                         onmouseout='this.style.borderColor=\"transparent\"; this.style.transform=\"scale(1)\";'>
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            # Botão com o nome do utilizador
                            if st.button(card['name'], key=f"btn_{i+j}", use_container_width=True):
                                if card['type'] == 'user':
                                    st.session_state.selected_profile = card['name']
                                else:
                                    st.session_state.creating_account = True
                                st.rerun()
