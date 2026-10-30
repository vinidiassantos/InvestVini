import streamlit as st
import yfinance as yf
import pandas as pd

# 1. Configuração da Página (Deve ser o primeiro comando Streamlit do app)
st.set_page_config(page_title="Meus Investimentos", page_icon="💰", layout="wide")

# ==========================================
# 2. TRAVA DE SEGURANÇA (PROTEÇÃO POR SENHA)
# ==========================================
if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

if not st.session_state.password_correct:
    st.title("🔒 Acesso Restrito")
    st.write("Este aplicativo é privado. Insira a senha para visualizar os investimentos.")
    
    password = st.text_input("Senha:", type="password")
    
    if st.button("Entrar"):
        # Compara a senha digitada com a que está no arquivo secrets.toml
        if password == st.secrets["app_password"]:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
            
    st.stop() # Interrompe a execução aqui se a senha estiver errada
# ==========================================

# A partir daqui, o código só roda se a pessoa acertar a senha!

st.title("💰 Dashboard de Investimentos")
st.markdown("Acompanhe suas ações, FIIs e o Tesouro Direto em um só lugar.")

# Função com cache para não sobrecarregar a API do Yahoo Finance
@st.cache_data(ttl=3600)
def buscar_dados(ativo):
    ticker = yf.Ticker(f"{ativo}.SA")
    # Puxa todo o histórico para calcularmos o mínimo histórico e de 12 meses
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
    
    # Puxando a lista de ações do cofre
    carteira_acoes = st.secrets["renda_variavel"]["carteira_acoes"]
    
    # Cria uma coluna para cada ação, garantindo que fiquem todas na horizontal
    cols = st.columns(len(carteira_acoes))

    for i, ativo in enumerate(carteira_acoes):
        hist = buscar_dados(ativo)
        
        if not hist.empty:
            preco_atual = hist['Close'].iloc[-1]
            preco_anterior = hist['Close'].iloc[-2]
            
            variacao_rs = preco_atual - preco_anterior
            variacao_pct = (variacao_rs / preco_anterior) * 100
            rsi = calcular_rsi(hist['Close'])
            
            # Cálculos de mínimo (Aproximadamente 252 dias úteis em 12 meses)
            min_12m = hist['Low'].tail(252).min()
            min_historico = hist['Low'].min()
            
            if rsi < 35:
                sinal = "COMPRAR"
                cor = "green"
            elif rsi > 70:
                sinal = "VENDER"
                cor = "red"
            else:
                sinal = "MANTER"
                cor = "gray"
                
            with cols[i]:
                with st.container(border=True):
                    # Título do Ativo
                    st.markdown(f"### **{ativo}**")
                    
                    # Cotação Atual e Variação
                    st.metric(
                        label="Atual", 
                        value=f"R$ {preco_atual:.2f}", 
                        delta=f"{variacao_pct:.2f}%"
                    )
                    
                    # Linhas com os novos dados (fonte menor para caber)
                    st.caption(f"📉 Mín 12m: **R$ {min_12m:.2f}**")
                    st.caption(f"⏳ Mín Hist: **R$ {min_historico:.2f}**")
                    
                    st.divider()
                    
                    # RSI e Sinal
                    st.markdown(f"**RSI:** {rsi:.1f}")
                    st.markdown(f"**Sinal:** :{cor}[**{sinal}**]")
                    
                    # Barra de progresso visual
                    st.progress(int(rsi))

# ==========================================
# ABA 2: TESOURO DIRETO (Lendo do Secrets)
# ==========================================
with aba_tesouro:
    st.subheader("Visão de Renda Fixa")
    
    # --- CARTEIRA FAMÍLIA ---
    st.markdown("### 👨‍👩‍👧‍👦 Família - Meta 500k")
    
    # Puxando os dados do cofre (secrets)
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
    
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.metric(label="Falta para a Meta (R$ 500.000)", value=st.secrets["familia"]["meta_falta"])
    with col_meta2:
        st.metric(label="Progresso da Meta", value=st.secrets["familia"]["meta_progresso"])
    
    st.divider()

    # --- CARTEIRA MARIA ---
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

    st.divider()

    # --- RESUMO GERAL ---
    st.markdown("### 📊 Resumo Geral Consolidado")
    col_res1, col_res2, col_res3 = st.columns(3)
    col_res1.metric("Total Investido", st.secrets["geral"]["total_investido"])
    col_res2.metric("Posição Atual", st.secrets["geral"]["posicao_atual"])
    col_res3.metric("Rentabilidade Global", st.secrets["geral"]["rentabilidade_global"])