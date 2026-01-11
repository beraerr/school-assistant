"""
Streamlit frontend for Smart School Information System
Turkish interface
"""
import streamlit as st
import requests
import pandas as pd
from typing import Optional

# Page configuration
st.set_page_config(
    page_title="Akıllı Okul Bilgi Sistemi",
    layout="wide"
)

# API base URL
API_BASE_URL = st.sidebar.text_input(
    "API URL",
    value="http://localhost:8000",
    help="FastAPI backend URL"
)

# Session state
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user" not in st.session_state:
    st.session_state.user = None


def login(username: str, password: str) -> bool:
    """Login to API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.access_token = data["access_token"]
            st.session_state.user = data["user"]
            return True
        else:
            st.error(f"Giriş hatası: {response.json().get('detail', 'Bilinmeyen hata')}")
            return False
    except Exception as e:
        st.error(f"Bağlantı hatası: {str(e)}")
        return False


def execute_query(query: str) -> Optional[dict]:
    """Execute natural language query"""
    if not st.session_state.access_token:
        st.error("Lütfen önce giriş yapın")
        return None
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        response = requests.post(
            f"{API_BASE_URL}/query/",
            json={"query": query},
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_detail = response.json().get("detail", "Bilinmeyen hata")
            st.error(f"Sorgu hatası: {error_detail}")
            return None
    except Exception as e:
        st.error(f"Bağlantı hatası: {str(e)}")
        return None


def get_role_display_name(role: str) -> str:
    """Get Turkish display name for role"""
    role_map = {
        "principal": "Müdür",
        "teacher": "Öğretmen",
        "parent": "Veli",
        "student": "Öğrenci"
    }
    return role_map.get(role, role)


# Main UI
st.title("Akıllı Okul Bilgi Sistemi")
st.markdown("---")

# Login section
if st.session_state.access_token is None:
    st.header("Giriş Yap")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        username = st.text_input("Kullanıcı Adı", key="login_username")
        password = st.text_input("Şifre", type="password", key="login_password")
        
        if st.button("Giriş Yap", type="primary"):
            if username and password:
                if login(username, password):
                    st.success("Giriş başarılı!")
                    st.rerun()
            else:
                st.warning("Lütfen kullanıcı adı ve şifre girin")
    
    with col2:
        st.info("""
        **Demo Kullanıcılar:**
        
        - Müdür: `principal` / `admin123`
        - Öğretmen: `teacher1` / `teacher123`
        - Veli: `parent1` / `parent123`
        - Öğrenci: `student1` / `student123`
        """)

else:
    # Logged in UI
    user = st.session_state.user
    
    # Sidebar with user info
    with st.sidebar:
        st.header("Kullanıcı Bilgileri")
        st.write(f"**Kullanıcı:** {user['username']}")
        st.write(f"**Rol:** {get_role_display_name(user['role'])}")
        if user.get('related_class'):
            st.write(f"**Sınıf:** {user['related_class']}")
        
        st.markdown("---")
        if st.button("Çıkış Yap"):
            st.session_state.access_token = None
            st.session_state.user = None
            st.rerun()
    
    # Main query interface
    st.header("Doğal Dil Sorgusu")
    st.markdown("Türkçe olarak sorularınızı sorun. Örnek: *'Bu ay devamsızlığı 5 günü geçen öğrencileri göster'*")
    
    # Example queries based on role
    example_queries = {
        "principal": [
            "Bu ay devamsızlığı 5 günü geçen öğrencileri göster",
            "Devamsızlık oranı en yüksek sınıflar hangileri?",
            "Tüm sınıfların ortalama notlarını göster"
        ],
        "teacher": [
            "Bu ay devamsızlığı 5 günü geçen öğrencileri göster",
            "Sınıfımdaki öğrencilerin matematik notlarını listele",
            "En yüksek not alan öğrencileri göster"
        ],
        "parent": [
            "Çocuğumun matematik notları geçen aya göre nasıl değişti?",
            "Çocuğumun bu ayki devamsızlık durumu nedir?",
            "Çocuğumun tüm ders notlarını göster"
        ],
        "student": [
            "Benim matematik notlarım geçen aya göre nasıl değişti?",
            "Bu ayki devamsızlık durumum nedir?",
            "Tüm ders notlarımı göster"
        ]
    }
    
    role = user['role']
    if role in example_queries:
        with st.expander("Örnek Sorgular"):
            for example in example_queries[role]:
                if st.button(example, key=f"example_{example}", use_container_width=True):
                    st.session_state.query_input = example
    
    # Query input
    query_input = st.text_area(
        "Sorgunuzu girin:",
        value=st.session_state.get("query_input", ""),
        height=100,
        key="query_input_main"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        submit_button = st.button("Sorguyu Çalıştır", type="primary", use_container_width=True)
    
    if submit_button and query_input:
        with st.spinner("Sorgu işleniyor..."):
            result = execute_query(query_input)
            
            if result:
                st.success("Sorgu başarıyla çalıştırıldı!")
                
                # Display results
                st.markdown("---")
                st.header("Sonuçlar")
                
                if result["results"]:
                    df = pd.DataFrame(result["results"])
                    st.dataframe(df, use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="CSV olarak indir",
                        data=csv,
                        file_name="sorgu_sonuclari.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Sorgu sonucu boş. Sonuç bulunamadı.")
                
                # Display explanation and metadata
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("AI Açıklaması")
                    st.info(result["explanation"])
                
                with col2:
                    st.subheader("Sorgu Bilgileri")
                    st.write(f"**Orijinal Sorgu:** {result['original_query']}")
                    st.write(f"**Sonuç Sayısı:** {result['results_count']}")
                    if result["permissions_applied"]:
                        st.warning(f"**İzin:** {result['permission_reason']}")
                    else:
                        st.success("**İzin:** Tüm verilere erişim")
                
                # SQL query (expandable)
                with st.expander("Oluşturulan SQL Sorgusu"):
                    st.code(result["sql_query"], language="sql")
    
    elif submit_button:
        st.warning("Lütfen bir sorgu girin")
