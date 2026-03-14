import streamlit as st
import pandas as pd
import os
from datetime import date, datetime
import database as db
import utils
import auth

st.set_page_config(page_title="Gestão de Projetos - Kanban", layout="wide", initial_sidebar_state="expanded")
st.markdown(utils.get_custom_css(), unsafe_allow_html=True)

db.init_db()
auth.init_session()

if not st.session_state.logged_in:
    auth.render_login_screen()
    st.stop()

logged_user = st.session_state.current_user

user_info = db.get_user(logged_user)
user_role = user_info[3] if user_info else "Membro"
user_avatar = user_info[4] if user_info else "https://api.dicebear.com/7.x/avataaars/svg?seed=Generico"

user_avatar_b64 = utils.get_image_base64(user_avatar)

all_users_data = db.get_all_users()
all_usernames = [u[0] for u in all_users_data]
user_avatars_dict = {u[0]: utils.get_image_base64(u[2]) for u in all_users_data}

MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_TYPES = ["pdf", "png", "jpg", "jpeg", "docx", "xlsx"]

# --- RENDERIZA MENSAGENS E ARQUIVOS ---
def render_chat_message(user_name, message, attachment, timestamp):
    avatar = user_avatars_dict.get(user_name, "https://api.dicebear.com/7.x/avataaars/svg?seed=Generico")
    time_str = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
    
    with st.chat_message(user_name, avatar=avatar):
        st.markdown(f"**{user_name}** &nbsp;<span style='font-size: 0.8em; color: gray;'>{time_str}</span>", unsafe_allow_html=True)
        if message: st.write(message)
        if attachment and os.path.exists(attachment):
            ext = attachment.split('.')[-1].lower()
            original_filename = os.path.basename(attachment).split('_', 1)[-1]
            if ext in ['png', 'jpg', 'jpeg', 'gif']:
                st.image(attachment, width=300)
            else:
                with open(attachment, "rb") as file:
                    st.download_button(label=f"📎 Baixar {original_filename}", data=file, file_name=original_filename)

# --- MODAL: DETALHES DA TAREFA E CHAT ---
@st.dialog("Detalhes da Tarefa")
def show_task_details(task_id, project_stages, all_users_list):
    task = db.get_task_by_id(task_id)
    if task:
        t_id, title, person, team, status, created_at, due_date, tags = task
        
        if tags:
            tags_html = ""
            for tag in tags.split(','):
                color = utils.TAGS_CONFIG.get(tag, "#888888")
                tags_html += f"<span class='tag-pill' style='background-color: {color};'>{tag}</span>"
            st.markdown(tags_html, unsafe_allow_html=True)
            
        st.subheader(title)
        tab_info, tab_chat = st.tabs(["📝 Detalhes", "💬 Chat da Tarefa"])
        
        with tab_info:
            c_info1, c_info2 = st.columns(2)
            c_info1.markdown(f"**👤 Atribuído a:** {person}")
            c_info2.markdown(f"**🏢 Equipa:** {team}")
            curr_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            st.markdown(f"**📅 Previsão:** {curr_date_obj.strftime('%d/%m/%Y')}")
            
            with st.popover("✏️ Editar Tarefa", use_container_width=True):
                with st.form(f"edit_task_form_{t_id}"):
                    st.write("**Atualizar Responsável e Prazo**")
                    idx = all_users_list.index(person) if person in all_users_list else 0
                    new_person = st.selectbox("Novo Responsável", all_users_list, index=idx)
                    new_date = st.date_input("Nova Data de Previsão", curr_date_obj)
                    if st.form_submit_button("Salvar Alterações", use_container_width=True):
                        db.update_task_info(t_id, new_person, new_date.isoformat())
                        st.success("Atualizado!")
                        st.rerun()

            st.divider()
            
            st.markdown("**Mover Tarefa para:**")
            col_move, col_btn = st.columns([3, 1])
            available_stages = [s for s in project_stages if s != status]
            
            with col_move:
                new_status = st.selectbox("Nova Etapa:", available_stages, label_visibility="collapsed")
            with col_btn:
                if st.button("Mover ➡️", use_container_width=True):
                    is_completed = (new_status == project_stages[-1])
                    db.update_status(t_id, new_status, is_completed)
                    st.rerun() 
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("🗑️ Excluir Tarefa", type="primary", use_container_width=True):
                db.delete_task(t_id)
                st.rerun()
                
        with tab_chat:
            chat_placeholder = st.empty()
            
            with st.form(f"form_comment_{t_id}", clear_on_submit=True):
                col_input, col_clip, col_btn = st.columns([6, 1, 2])
                with col_input:
                    new_comment = st.text_input("Comentário", placeholder="Escreva um comentário...", label_visibility="collapsed")
                with col_clip:
                    with st.popover("📎", use_container_width=True):
                        uploaded_file = st.file_uploader(f"Máx: {MAX_FILE_SIZE_MB}MB", type=ALLOWED_TYPES, key=f"file_task_{t_id}")
                with col_btn:
                    submit_btn = st.form_submit_button("Enviar", use_container_width=True)
                
                if submit_btn:
                    if uploaded_file and uploaded_file.size > MAX_FILE_SIZE_BYTES:
                        st.error(f" O ficheiro é muito pesado! O limite é de {MAX_FILE_SIZE_MB}MB.")
                    elif new_comment or uploaded_file:
                        file_path = utils.save_uploaded_file(uploaded_file)
                        db.add_task_comment(t_id, logged_user, new_comment, file_path)
            
            with chat_placeholder.container(height=300):
                comments = db.get_task_comments(t_id)
                if not comments: st.caption("Nenhum comentário ainda.")
                for c_user, c_msg, c_att, c_time in comments: 
                    render_chat_message(c_user, c_msg, c_att, c_time)

def move_stage_callback(s_id, s_order, other_id, other_order):
    db.swap_stage_order(s_id, s_order, other_id, other_order)

@st.dialog(" Configurar Colunas")
def manage_columns_dialog(project_id):
    st.markdown("Altere os nomes das etapas ou mova-as de posição:")
    st.write("<br>", unsafe_allow_html=True)
    stages = db.get_project_stages_detailed(project_id)
    for i, (s_id, s_name, s_order) in enumerate(stages):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([4, 1, 1, 1])
            with c1: 
                st.markdown(f"<h5 style='margin-bottom:0;'>{s_name}</h5>", unsafe_allow_html=True)
            with c2:
                with st.popover("✏️", use_container_width=True):
                    new_stage_name = st.text_input("Renomear Coluna", value=s_name, key=f"rn_{s_id}")
                    if st.button("Salvar Novo Nome", key=f"btn_rn_{s_id}", use_container_width=True):
                        db.rename_stage(s_id, new_stage_name)
                        st.rerun()
            with c3:
                if i > 0:
                    prev_id, _, prev_order = stages[i-1]
                    st.button("⬅️", key=f"left_{s_id}", use_container_width=True, on_click=move_stage_callback, args=(s_id, s_order, prev_id, prev_order))
            with c4:
                if i < len(stages) - 1:
                    next_id, _, next_order = stages[i+1]
                    st.button("➡️", key=f"right_{s_id}", use_container_width=True, on_click=move_stage_callback, args=(s_id, s_order, next_id, next_order))
    st.divider()
    if st.button("✅ Concluir e Atualizar Quadro", use_container_width=True, type="primary"): st.rerun()

# --- MENU LATERAL ---
with st.sidebar:
    st.markdown(f"<div style='text-align: center;'><img src='{user_avatar_b64}' style='width: 100px; height: 100px; border-radius: 50%; object-fit: cover; box-shadow: 0px 4px 8px rgba(0,0,0,0.2);'></div>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: center;'>{logged_user}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray; margin-top: -10px;'>{user_role}</p>", unsafe_allow_html=True)
    
    with st.popover("⚙️ Editar Perfil", use_container_width=True):
        st.write("**Alterar Foto de Perfil**")
        new_avatar_file = st.file_uploader("Escolha uma imagem", type=["png", "jpg", "jpeg"], key="avatar_uploader")
        if st.button("Salvar Nova Foto", use_container_width=True):
            if new_avatar_file:
                if new_avatar_file.size > MAX_FILE_SIZE_BYTES:
                    st.error(f"A imagem deve ter no máximo {MAX_FILE_SIZE_MB}MB.")
                else:
                    avatar_path = utils.save_uploaded_file(new_avatar_file)
                    db.update_user_avatar(logged_user, avatar_path)
                    st.success("Foto atualizada! A recarregar...")
                    st.rerun()
            else:
                st.warning("Nenhum ficheiro selecionado.")

    if st.button(" Sair", use_container_width=True):
        auth.logout()
        st.rerun()
        
    st.divider()
    st.header("📂 Projetos")
    projects = db.get_projects()
    selected_project_id = None
    if projects:
        proj_dict = {p[1]: p[0] for p in projects}
        selected_project_name = st.selectbox("Projeto Ativo", list(proj_dict.keys()), label_visibility="collapsed")
        selected_project_id = proj_dict[selected_project_name]
    else:
        st.warning("Nenhum projeto encontrado.")
        
    with st.popover(" Novo Projeto", use_container_width=True):
        with st.form("new_project_form", clear_on_submit=True):
            new_proj_name = st.text_input("Nome do Projeto")
            col_d1, col_d2 = st.columns(2)
            with col_d1: start_date = st.date_input("Início", date.today())
            with col_d2: end_date = st.date_input("Fim", date.today())
            if st.form_submit_button("Criar") and new_proj_name:
                if start_date > end_date: st.error("A data de fim deve ser posterior ao início!")
                else:
                    if not db.add_project(new_proj_name, start_date.isoformat(), end_date.isoformat()): st.error("Projeto já existe!")
                    else: st.rerun()

# --- ÁREA PRINCIPAL ---
if selected_project_id:
    stages = db.get_project_stages(selected_project_id)
    st.title(f" {selected_project_name}")
    st.write("<br>", unsafe_allow_html=True)

    tab_kanban, tab_metrics, tab_chat = st.tabs(["📋 Quadro Kanban", "📊 Dashboards", "💬 Chat do Projeto"])

    # ==========================================
    # ABA 1: KANBAN
    # ==========================================
    with tab_kanban:
        with st.expander(" Adicionar Nova Tarefa", expanded=False):
            with st.form("new_task_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    title = st.text_input("Título da Tarefa*")
                    idx = all_usernames.index(logged_user) if logged_user in all_usernames else 0
                    person = st.selectbox("Atribuir a*", all_usernames, index=idx)
                    selected_tags = st.multiselect("Tags Especiais", list(utils.TAGS_CONFIG.keys()))
                with col2:
                    team_group = st.selectbox("Grupo / Equipa", ["Frontend", "Backend", "Design", "Banco de Dados", "Negócios", "Infraestrutura"])
                    due_date_input = st.date_input("Data de Previsão de Término*")
                
                if st.form_submit_button("Salvar Tarefa"):
                    if title:
                        if due_date_input < date.today(): st.error("A data de término não pode ser no passado!")
                        else:
                            tags_str = ",".join(selected_tags) if selected_tags else ""
                            db.add_task(selected_project_id, title, person, team_group, due_date_input, status=stages[0], tags=tags_str)
                            st.success("Tarefa adicionada!")
                            st.rerun()
                    else: st.error("O Título é obrigatório.")

        st.divider()
        col_filter, col_add_stage, col_reorder = st.columns([3, 1, 1]) 
        
        with col_filter:
            selected_teams_filter = st.multiselect("🔍 Filtrar por Equipa:", ["Frontend", "Backend", "Design", "Banco de Dados", "Negócios", "Infraestrutura"], placeholder="Selecione as equipas (vazio mostra todas)")
            
        with col_add_stage:
            st.write("<br>", unsafe_allow_html=True) 
            with st.popover(" Nova Coluna", use_container_width=True):
                with st.form("new_stage_form", clear_on_submit=True):
                    new_stage_name = st.text_input("Nome da Nova Etapa")
                    if st.form_submit_button("Criar") and new_stage_name:
                        db.add_project_stage(selected_project_id, new_stage_name)
                        st.rerun()
                        
        with col_reorder:
            st.write("<br>", unsafe_allow_html=True) 
            if st.button(" Configurar Colunas", use_container_width=True): manage_columns_dialog(selected_project_id)
        
        st.write("<br>", unsafe_allow_html=True)
        kanban_cols = st.columns(len(stages))

        def render_column_grouped(col_obj, status_name, is_last_stage):
            with col_obj:
                emoji = "✅" if is_last_stage else ("📝" if status_name == "A Fazer" else ("⚙️" if status_name == "Em Progresso" else "📌"))
                st.subheader(f"{emoji} {status_name}")
                tasks = db.get_tasks(selected_project_id, status_name)
                if selected_teams_filter: tasks = [t for t in tasks if t[3] in selected_teams_filter]
                if not tasks:
                    st.caption("Nenhuma tarefa aqui.")
                    return

                grouped_tasks = {}
                for t in tasks:
                    team = t[3] 
                    if team not in grouped_tasks: grouped_tasks[team] = []
                    grouped_tasks[team].append(t)
                
                
                # ==========================================
                for team, team_tasks in grouped_tasks.items():
                    # O expander_title exibe o nome da equipa e a quantidade de tarefas!
                    expander_title = f"🏢 {team} ({len(team_tasks)} tarefas)"
                    
                    with st.expander(expander_title, expanded=True):
                        for t in team_tasks:
                            t_id, title, person, team_name, status, created_at, due_date, tags = t
                            is_my_task = person == logged_user
                            
                            with st.container(border=True):
                                if tags:
                                    tags_html = ""
                                    for tag in tags.split(','):
                                        color = utils.TAGS_CONFIG.get(tag, "#888888")
                                        tags_html += f"<span class='tag-pill' style='background-color: {color};'>{tag}</span>"
                                    st.markdown(tags_html, unsafe_allow_html=True)
                                
                                marker = "📌 " if is_my_task else ""
                                if st.button(f"{marker}📄 {title}\n(👤 {person})", key=f"btn_{t_id}", use_container_width=True):
                                    show_task_details(t_id, stages, all_usernames)
                                
                                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
                                date_str_br = due_date_obj.strftime('%d/%m/%Y')
                                
                                if is_last_stage: st.success(f"Finalizado! ({date_str_br})")
                                elif date.today() > due_date_obj: st.error(f"🚨 Atrasado! ({date_str_br})")
                                else: st.progress(utils.calculate_progress(created_at, due_date, is_last_stage), text=f"Prazo: {date_str_br}")

        for i, stage in enumerate(stages):
            is_last = (i == len(stages) - 1)
            render_column_grouped(kanban_cols[i], stage, is_last)

    # ==========================================
    # ABA 2: DASHBOARDS E MÉTRICAS
    # ==========================================
    with tab_metrics:
        st.markdown("###  Visão Geral do Projeto")
        tasks_data = db.get_all_tasks(selected_project_id)
        if not tasks_data: st.info("Crie algumas tarefas no Kanban para visualizar os gráficos.")
        else:
            df = pd.DataFrame(tasks_data, columns=['id', 'title', 'person', 'team_group', 'status', 'created_at', 'due_date', 'completed_at', 'tags'])
            total_tasks = len(df)
            completed_tasks = len(df[df['status'] == stages[-1]])
            completion_pct = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total de Tarefas", total_tasks)
            c2.metric("Tarefas Concluídas", completed_tasks)
            c3.metric("Trabalho Restante", total_tasks - completed_tasks)
            c4.metric("Progresso Geral", f"{completion_pct}%")
            st.divider()
            
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("##### Tarefas por Etapa")
                stage_counts = df['status'].value_counts().reset_index()
                stage_counts.columns = ['Etapa', 'Quantidade']
                st.bar_chart(stage_counts.set_index('Etapa'), color="#4F8BF9")
            with col_chart2:
                st.markdown("##### Tarefas por Pessoa")
                person_counts = df['person'].value_counts().reset_index()
                person_counts.columns = ['Pessoa', 'Quantidade']
                st.bar_chart(person_counts.set_index('Pessoa'), color="#F99F4F")
            st.divider()

            st.markdown("##### Burndown Chart (Trabalho Restante vs Ritmo Ideal)")
            st.caption("A linha **Ideal** baseia-se na data de início e fim que definiu para o projeto. A linha **Real** acompanha as suas conclusões.")
            project_info = db.get_project_info(selected_project_id)
            if project_info and project_info[1] and project_info[2]:
                _, p_start, p_end = project_info
                min_date = pd.to_datetime(p_start)
                max_date = pd.to_datetime(p_end)
                if min_date <= max_date:
                    date_range = pd.date_range(start=min_date, end=max_date)
                    burndown_df = pd.DataFrame({'Data': date_range})
                    days_total = (max_date - min_date).days
                    ideal_values = []
                    for i in range(len(date_range)):
                        if days_total > 0: val = total_tasks - ((total_tasks / days_total) * i)
                        else: val = 0
                        ideal_values.append(max(0, val))
                    burndown_df['Ideal'] = ideal_values
                    completed_dates = pd.to_datetime(df['completed_at']).dropna()
                    actual_remaining = []
                    today_ts = pd.Timestamp(date.today())
                    for d in date_range:
                        if d.date() > today_ts.date(): actual_remaining.append(float('nan')) 
                        else:
                            completed_count = sum(completed_dates.dt.date <= d.date())
                            actual_remaining.append(float(total_tasks - completed_count))
                    burndown_df['Real'] = actual_remaining
                    burndown_df.set_index('Data', inplace=True)
                    st.line_chart(burndown_df[['Ideal', 'Real']], color=["#AAAAAA", "#4F8BF9"])
                else: st.warning("As datas do projeto são inválidas para o Burndown.")
            else: st.warning("Este projeto não tem datas de início e fim definidas para gerar o gráfico.")

    # ==========================================
    # ABA 3: CHAT DO PROJETO
    # ==========================================
    with tab_chat:
        col_space_left, col_chat_center, col_space_right = st.columns([1, 4, 1])
        with col_chat_center:
            tab_geral, tab_dm = st.tabs([" Geral do Projeto", " Mensagens Privadas"])
            
            with tab_geral:
                chat_placeholder_geral = st.empty()
                with st.form("form_proj_chat", clear_on_submit=True):
                    col_input, col_clip, col_btn = st.columns([6, 1, 2])
                    with col_input:
                        msg = st.text_input("Mensagem", placeholder="Mensagem para a equipa...", label_visibility="collapsed")
                    with col_clip:
                        with st.popover("📎", use_container_width=True):
                            uploaded_file = st.file_uploader(f"Máx: {MAX_FILE_SIZE_MB}MB", type=ALLOWED_TYPES, key="file_geral")
                    with col_btn:
                        submit_btn = st.form_submit_button("Enviar", use_container_width=True)
                    
                    if submit_btn:
                        if uploaded_file and uploaded_file.size > MAX_FILE_SIZE_BYTES:
                            st.error(f"⚠️ O ficheiro é muito pesado! O limite é de {MAX_FILE_SIZE_MB}MB.")
                        elif msg or uploaded_file:
                            file_path = utils.save_uploaded_file(uploaded_file)
                            db.add_project_chat(selected_project_id, logged_user, msg, file_path)
                            
                with chat_placeholder_geral.container(height=500, border=True):
                    proj_chats = db.get_project_chats(selected_project_id)
                    if not proj_chats: st.caption("Sem mensagens no projeto.")
                    for p_user, p_msg, p_att, p_time in proj_chats: 
                        render_chat_message(p_user, p_msg, p_att, p_time)

            with tab_dm:
                other_users = [u for u in all_usernames if u != logged_user]
                if other_users:
                    chat_partner = st.selectbox("Conversar com:", other_users)
                    chat_placeholder_dm = st.empty()
                    with st.form("form_dm_chat", clear_on_submit=True):
                        col_input, col_clip, col_btn = st.columns([6, 1, 2])
                        with col_input:
                            dm_msg = st.text_input("Sua mensagem privada", placeholder="A sua mensagem...", label_visibility="collapsed")
                        with col_clip:
                            with st.popover("📎", use_container_width=True):
                                uploaded_file = st.file_uploader(f"Máx: {MAX_FILE_SIZE_MB}MB", type=ALLOWED_TYPES, key="file_dm")
                        with col_btn:
                            submit_btn = st.form_submit_button("Enviar", use_container_width=True)
                            
                        if submit_btn:
                            if uploaded_file and uploaded_file.size > MAX_FILE_SIZE_BYTES:
                                st.error(f" O ficheiro é muito pesado! O limite é de {MAX_FILE_SIZE_MB}MB.")
                            elif dm_msg or uploaded_file:
                                file_path = utils.save_uploaded_file(uploaded_file)
                                db.add_direct_message(logged_user, chat_partner, dm_msg, file_path)
                                
                    with chat_placeholder_dm.container(height=425, border=True):
                        dm_chats = db.get_direct_messages(logged_user, chat_partner)
                        if not dm_chats: st.caption(f"Envie um olá a {chat_partner}!")
                        for d_sender, d_msg, d_att, d_time in dm_chats: 
                            render_chat_message(d_sender, d_msg, d_att, d_time)
                else:
                    st.info("Ainda não existem outros utilizadores registados.")

else:
    st.title("Bem-vindo ao Kanban")
    st.info("👈 Comece selecionando ou criando um novo projeto no menu lateral.")