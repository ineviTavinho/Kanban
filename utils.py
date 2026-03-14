import os
import base64
from datetime import date, datetime
import streamlit as st
import requests

TAGS_CONFIG = {
    "🔴 Urgente": "#FF4B4B",
    "🔵 Melhoria": "#1C83E1",
    "🐛 Bug": "#FFA421",
    "✨ Nova Feature": "#00C04B",
    "📚 Documentação": "#808495"
}

def save_uploaded_file(uploaded_file):
    if uploaded_file is not None:
        api_url = st.secrets.get("SUPABASE_API_URL")
        api_key = st.secrets.get("SUPABASE_KEY")
        
        # Cria um nome único com a data para não sobrepor ficheiros com o mesmo nome
        ts = datetime.now().strftime("%Y%m%d%H%M%S_")
        safe_name = ts + uploaded_file.name.replace(" ", "_")
        
        # Endpoint do Supabase Storage
        endpoint = f"{api_url}/storage/v1/object/kanban/{safe_name}"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "apikey": api_key,
            "Content-Type": uploaded_file.type
        }
        
        # Envia o ficheiro para o "balde" da nuvem
        response = requests.post(endpoint, headers=headers, data=uploaded_file.getvalue())
        
        if response.status_code == 200:
            # Retorna o link público e definitivo da imagem!
            return f"{api_url}/storage/v1/object/public/kanban/{safe_name}"
        else:
            st.error("Erro ao salvar ficheiro na nuvem do Supabase.")
            return None
    return None

def get_image_base64(image_path):
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                encoded = base64.b64encode(img_file.read()).decode()
                ext = image_path.split('.')[-1].lower()
                mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                return f"data:{mime};base64,{encoded}"
        except Exception:
            return image_path
    return image_path

def calculate_progress(created_at_str, due_date_str, status):
    if status == "Concluído": return 1.0
    created = datetime.strptime(created_at_str, "%Y-%m-%d").date()
    due = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    today = date.today()
    total_days = (due - created).days
    elapsed_days = (today - created).days
    if total_days <= 0: return 1.0
    progress = elapsed_days / total_days
    return max(0.0, min(1.0, progress))

def get_custom_css():
    return """
    <style>
        .profile-link { text-decoration: none !important; color: inherit !important; }
        .avatar-card { transition: transform 0.2s ease-in-out; display: flex; flex-direction: column; align-items: center; padding: 20px 10px; border-radius: 20px; }
        .avatar-card:hover { transform: scale(1.15); cursor: pointer; }
        .avatar-img { width: 140px; height: 140px; border-radius: 50%; object-fit: cover; box-shadow: 0px 8px 16px rgba(0,0,0,0.3); border: 4px solid transparent; transition: border-color 0.2s; }
        .avatar-card:hover .avatar-img { border-color: #4F8BF9; }
        .avatar-name { margin-top: 15px; font-size: 24px; font-weight: 600; color: inherit; }
        
        .tag-pill {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-right: 5px;
            margin-bottom: 8px;
            color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
    </style>
    """
