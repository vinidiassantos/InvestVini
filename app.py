import streamlit as st
import yfinance as yf
import pandas as pd
import extra_streamlit_components as stx
import hashlib
from datetime import datetime, timedelta

# 1. Configuração da Página
st.set_page_config(page_title="DinDin", page_icon="💰", layout="wide")

# Inicializa o gerenciador de cookies
cookie_manager = stx.CookieManager(key="cookie_dindin")

# ==========================================
# 2. TRAVA DE SEGURANÇA (COM COOKIES)
# ==========================================
# Criamos um hash da sua senha para não salvar a senha em texto puro no cookie
token_seguranca = hashlib.sha256(st.secrets["app_password"].encode()).hexdigest()

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

# Tenta ler o cookie para ver se o usuário já logou antes
auth_cookie = cookie_manager.get(cookie="dindin_auth")

# Se o cookie for válido, loga automaticamente
if not st.session_state.password_correct and auth_cookie == token_seguranca:
    st.session_state.password_correct = True

# Se não estiver logado, mostra a tela de senha
if not st.session_state.password_correct:
    st.title("🔒 Acesso Restrito")
    st.write("Este aplicativo é privado. Insira a senha para visualizar os investimentos.")
    
    password = st.text_input("Senha:", type="password")
    
    if st.button("Entrar"):
        if password == st.secrets["app_password"]:
            st.session_state.password_correct = True
            # Salva o cookie no navegador por 7 dias
            cookie_manager.set(
                "dindin_auth", 
                token_seguranca, 
                expires_at=datetime.now() + timedelta(days=7)
            )
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
            
    st.stop() 
# ==========================================

# A partir daqui, o código só roda se a pessoa estiver logada!

# Botão de Logout na barra lateral
with st.sidebar:
    st.write("---")
    if st.button("Sair do App"):
        cookie_manager.delete("dindin_auth")
        st.session_state.password_correct = False
        st.rerun()

# ==========================================
# CABEÇALHO (Título + KPIs Consolidados + Meta)
# ==========================================
col_titulo, col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns([2, 1, 1, 1, 1.2])

with col_titulo:
    st.title("💰 DinDin")
    st.markdown("Seus investimentos e dicas em um só lugar.")

with col_kpi1:
    st.write("") 
    st.write("")
    st.metric(label="Total Investido", value=st.secrets["geral"]["total_investido"])

with col_kpi2:
    st.write("")
    st.write("")
    st.metric(label="Posição Atual", value=st.secrets["geral"]["posicao_atual"])

with col_kpi3:
    st.write("")
    st.write("")
    st.metric(label="Rentabilidade Global", value=st.secrets["geral"]["rentabilidade_global"])

with col_kpi4:
    st.write("")
    st.write("")
    st.metric(label="Meta Família", value=st.secrets["familia"]["meta_progresso"])
    st.caption(f"Falta: {st.secrets['familia']['meta_falta']}")

st.divider()

# Função com cache
@st.cache_data(ttl=3600)
def buscar_dados(ativo):
    ticker = yf.Ticker(f"{ativo}.SA")
    return ticker.history(period="max")

def calcular_rsi(dados, periodo=14):
    delta = dados.diff(1)
    ganho = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
    rs = ganho / perda
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

# Criando as Abas
aba_renda_variavel, aba_tesouro = st.tabs(["📈 Renda Variável (Ações e FIIs)", "🏦 Tesouro Direto"])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Cotações e Sinais do Robô")
    
    carteira_acoes = st.secrets["renda_variavel"]["carteira_acoes"]
    
    cols = st.columns(len(carteira_acoes))

    for i, ativo in enumerate(carteira_acoes):
        hist = buscar_dados(ativo)
        
        if not hist.empty:
            preco_atual = hist['Close'].iloc[-1]
            preco_anterior = hist['Close'].iloc[-2]
            
            variacao_rs = preco_atual - preco_anterior
            variacao_pct = (variacao_rs / preco_anterior) * 100
            rsi = calcular_rsi(hist['Close'])
            
            min_12m = hist['Low'].tail(252).min()
            min_historico = hist['Low'].min()
            
            if rsi < 35:
                sinal = "COMPRAR"
                cor = "#00FF00"
            elif rsi > 70:
                sinal = "VENDER"
                cor = "#FF4B4B"
            else:
                sinal = "MANTER"
                cor = "#808080"
                
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"<h4 style='text-align: center; margin-top: 0; margin-bottom: 5px;'>{ativo}</h4>", unsafe_allow_html=True)
                    
                    st.metric(label="Cotação Atual", value=f"R$ {preco_atual:.2f}", delta=f"{variacao_pct:.2f}%", label_visibility="collapsed")
                    
                    st.markdown(
                        f"""
                        <div style="font-size: 13px; line-height: 1.6; margin-bottom: 10px;">
                            📉 <b>Mín 12m:</b> R$ {min_12m:.2f}<br>
                            ⏳ <b>Mín Hist:</b> R$ {min_historico:.2f}<br>
                            📊 <b>RSI:</b> {rsi:.1f}<br>
                            🤖 <b>Sinal:</b> <span style="color:{cor}; font-weight: bold;">{sinal}</span>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
                    
                    st.progress(int(rsi))

# ==========================================
# ABA 2: TESOURO DIRETO (Separado por Containers)
# ==========================================
with aba_tesouro:
    st.subheader("Visão de Renda Fixa")
    
    # --- CARTEIRA FAMÍLIA ---
    with st.container(border=True):
        st.markdown("### 👨‍👩‍👧‍👦 Família - Meta 500k")
        
        df_familia = pd.DataFrame({
            "Ativo": st.secrets["familia"]["ativos"],
            "Investido (R$)": st.secrets["familia"]["investido"],
            "Posição Atual (R$)": st.secrets["familia"]["posicao"],
            "Ganho (R$)": st.secrets["familia"]["ganho"],
            "Rentabilidade (%)": st.secrets["familia"]["rentabilidade"]
        })
        
        st.dataframe(
            df_familia, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Investido (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Posição Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Ganho (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Rentabilidade (%)": st.column_config.NumberColumn(format="%.2f%%")
            }
        )

    st.write("") 

    # --- CARTEIRA MARIA (Intacta) ---
    with st.container(border=True):
        st.markdown("### 👩 Maria Invest")
        
        df_maria = pd.DataFrame({
            "Ativo": st.secrets["maria"]["ativos"],
            "Investido (R$)": st.secrets["maria"]["investido"],
            "Posição Atual (R$)": st.secrets["maria"]["posicao"],
            "Ganho (R$)": st.secrets["maria"]["ganho"],
            "Rentabilidade (%)": st.secrets["maria"]["rentabilidade"]
        })
        
        st.dataframe(
            df_maria, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Investido (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Posição Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Ganho (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Rentabilidade (%)": st.column_config.NumberColumn(format="%.2f%%")
            }
        )