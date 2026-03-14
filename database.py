import psycopg2
from psycopg2 import IntegrityError
from datetime import date, datetime, timedelta
import streamlit as st

def get_connection():
    try:
        # Apenas pega o link (que agora já tem o sslmode e pgbouncer embutidos)
        url = st.secrets["SUPABASE_URL"]
        return psycopg2.connect(url)
    except Exception as e:
        st.error(f"🔴 Erro crítico de conexão com a Nuvem: {e}")
        raise e

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT, avatar_url TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY, name TEXT UNIQUE, start_date TEXT, end_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY, project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE, 
                    title TEXT, person TEXT, team_group TEXT, status TEXT, 
                    created_at TEXT, due_date TEXT, completed_at TEXT, tags TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_stages (
                    id SERIAL PRIMARY KEY, project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE, 
                    name TEXT, order_index INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS task_comments (
                    id SERIAL PRIMARY KEY, task_id INTEGER, "user" TEXT, message TEXT, attachment TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS project_chats (
                    id SERIAL PRIMARY KEY, project_id INTEGER, "user" TEXT, message TEXT, attachment TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS direct_messages (
                    id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, message TEXT, attachment TEXT, timestamp TEXT)''')
    
    # Mantemos apenas a criação do utilizador inicial (Gustavo Andrew)
    c.execute('SELECT count(*) FROM users')
    if c.fetchone()[0] == 0:
        avatar = "https://api.dicebear.com/7.x/avataaars/svg?seed=Gustavo&backgroundColor=b6e3f4"
        c.execute('INSERT INTO users (username, password, role, avatar_url) VALUES (%s, %s, %s, %s)', 
                  ("Gustavo Andrew", "123", "Administrador", avatar))
    
    # REMOVIDA a injeção automática do Projeto Alpha!
            
    conn.commit()
    conn.close()

# --- FUNÇÕES DE UTILIZADORES ---
def add_user(username, password, role, avatar_url):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password, role, avatar_url) VALUES (%s, %s, %s, %s)', 
                  (username, password, role, avatar_url))
        conn.commit()
        return True
    except IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_user(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, password, role, avatar_url FROM users WHERE username = %s', (username,))
    data = c.fetchone()
    conn.close()
    return data

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT username, role, avatar_url FROM users ORDER BY username ASC')
    data = c.fetchall()
    conn.close()
    return data

def update_user_avatar(username, new_avatar_url):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET avatar_url = %s WHERE username = %s', (new_avatar_url, username))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE PROJETOS E TAREFAS ---
def add_project(name, start_date, end_date):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO projects (name, start_date, end_date) VALUES (%s, %s, %s) RETURNING id', (name, start_date, end_date))
        project_id = c.fetchone()[0]
        c.execute("INSERT INTO project_stages (project_id, name, order_index) VALUES (%s, 'A Fazer', 0)", (project_id,))
        c.execute("INSERT INTO project_stages (project_id, name, order_index) VALUES (%s, 'Em Progresso', 1)", (project_id,))
        c.execute("INSERT INTO project_stages (project_id, name, order_index) VALUES (%s, 'Concluído', 2)", (project_id,))
        conn.commit()
        return True
    except IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_projects():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name FROM projects ORDER BY id DESC')
    data = c.fetchall()
    conn.close()
    return data

def get_project_info(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT name, start_date, end_date FROM projects WHERE id = %s', (project_id,))
    data = c.fetchone()
    conn.close()
    return data

def get_project_stages(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT name FROM project_stages WHERE project_id = %s ORDER BY order_index ASC', (project_id,))
    data = c.fetchall()
    conn.close()
    return [row[0] for row in data]

def get_project_stages_detailed(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, name, order_index FROM project_stages WHERE project_id = %s ORDER BY order_index ASC', (project_id,))
    data = c.fetchall()
    conn.close()
    return data

def add_project_stage(project_id, stage_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT MAX(order_index) FROM project_stages WHERE project_id = %s', (project_id,))
    max_idx = c.fetchone()[0]
    next_idx = 0 if max_idx is None else max_idx + 1
    c.execute('INSERT INTO project_stages (project_id, name, order_index) VALUES (%s, %s, %s)', (project_id, stage_name, next_idx))
    conn.commit()
    conn.close()

def swap_stage_order(stage1_id, stage1_order, stage2_id, stage2_order):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE project_stages SET order_index = %s WHERE id = %s', (stage2_order, stage1_id))
    c.execute('UPDATE project_stages SET order_index = %s WHERE id = %s', (stage1_order, stage2_id))
    conn.commit()
    conn.close()

def rename_stage(stage_id, new_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE project_stages SET name = %s WHERE id = %s', (new_name, stage_id))
    conn.commit()
    conn.close()

def add_task(project_id, title, person, team_group, due_date, status, tags=""):
    conn = get_connection()
    c = conn.cursor()
    created_at = date.today().isoformat()
    due_date_str = due_date.isoformat()
    c.execute('''INSERT INTO tasks (project_id, title, person, team_group, status, created_at, due_date, completed_at, tags) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s)''', 
              (project_id, title, person, team_group, status, created_at, due_date_str, tags))
    conn.commit()
    conn.close()

def get_tasks(project_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, person, team_group, status, created_at, due_date, tags FROM tasks WHERE project_id = %s AND status = %s', (project_id, status))
    data = c.fetchall()
    conn.close()
    return data

def get_task_by_id(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, person, team_group, status, created_at, due_date, tags FROM tasks WHERE id = %s', (task_id,))
    data = c.fetchone()
    conn.close()
    return data

def get_all_tasks(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, title, person, team_group, status, created_at, due_date, completed_at, tags FROM tasks WHERE project_id = %s', (project_id,))
    data = c.fetchall()
    conn.close()
    return data

def update_status(task_id, new_status, is_completed=False):
    conn = get_connection()
    c = conn.cursor()
    if is_completed:
        completed_at = date.today().isoformat()
        c.execute('UPDATE tasks SET status = %s, completed_at = %s WHERE id = %s', (new_status, completed_at, task_id))
    else:
        c.execute('UPDATE tasks SET status = %s, completed_at = NULL WHERE id = %s', (new_status, task_id))
    conn.commit()
    conn.close()

def update_task_info(task_id, new_person, new_due_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE tasks SET person = %s, due_date = %s WHERE id = %s', (new_person, new_due_date, task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    conn.commit()
    conn.close()

# --- FUNÇÕES DE CHAT ---
def add_task_comment(task_id, user, message, attachment=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO task_comments (task_id, "user", message, attachment, timestamp) VALUES (%s, %s, %s, %s, %s)', 
              (task_id, user, message, attachment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_task_comments(task_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT "user", message, attachment, timestamp FROM task_comments WHERE task_id = %s ORDER BY id ASC', (task_id,))
    data = c.fetchall()
    conn.close()
    return data

def add_project_chat(project_id, user, message, attachment=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO project_chats (project_id, "user", message, attachment, timestamp) VALUES (%s, %s, %s, %s, %s)', 
              (project_id, user, message, attachment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_project_chats(project_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT "user", message, attachment, timestamp FROM project_chats WHERE project_id = %s ORDER BY id ASC', (project_id,))
    data = c.fetchall()
    conn.close()
    return data

def add_direct_message(sender, receiver, message, attachment=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('INSERT INTO direct_messages (sender, receiver, message, attachment, timestamp) VALUES (%s, %s, %s, %s, %s)', 
              (sender, receiver, message, attachment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_direct_messages(user1, user2):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT sender, message, attachment, timestamp FROM direct_messages 
                 WHERE (sender = %s AND receiver = %s) OR (sender = %s AND receiver = %s) 
                 ORDER BY id ASC''', (user1, user2, user2, user1))
    data = c.fetchall()
    conn.close()
    return data
