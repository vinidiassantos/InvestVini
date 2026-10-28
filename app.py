import streamlit as st
import yfinance as yf
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="Meus Investimentos", page_icon="💰", layout="wide")

st.title("💰 Dashboard de Investimentos")
st.markdown("Acompanhe suas ações, FIIs e o Tesouro Direto em um só lugar.")

# Criando as Abas
aba_renda_variavel, aba_tesouro = st.tabs(["📈 Renda Variável (Ações e FIIs)", "🏦 Tesouro Direto"])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Cotações e Sinais do Robô")
    
    carteira_acoes = ['VALE3', 'WEGE3', 'ITSA4', 'BOVA11', 'CEAB3', 'XPML11', 'MCCI11']
    
    def calcular_rsi(dados, periodo=14):
        delta = dados.diff(1)
        ganho = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
        rs = ganho / perda
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    cols = st.columns(3)

    for i, ativo in enumerate(carteira_acoes):
        ticker = yf.Ticker(f"{ativo}.SA")
        hist = ticker.history(period="2mo")
        
        if not hist.empty:
            preco_atual = hist['Close'].iloc[-1]
            preco_anterior = hist['Close'].iloc[-2]
            
            # Delta (Variação)
            variacao_rs = preco_atual - preco_anterior
            variacao_pct = (variacao_rs / preco_anterior) * 100
            
            # RSI e Sinal
            rsi = calcular_rsi(hist['Close'])
            
            if rsi < 35:
                sinal = "🟢 COMPRAR"
                cor = "green"
            elif rsi > 70:
                sinal = "🔴 VENDER"
                cor = "red"
            else:
                sinal = "⚪ MANTER"
                cor = "gray"
                
            with cols[i % 3]:
                with st.container(border=True):
                    st.subheader(ativo)
                    st.metric(
                        label="Cotação Atual", 
                        value=f"R$ {preco_atual:.2f}", 
                        delta=f"{variacao_pct:.2f}% (R$ {variacao_rs:.2f})"
                    )
                    st.markdown(f"**RSI:** {rsi:.1f}")
                    st.markdown(f"**Sinal do Robô:** :{cor}[{sinal}]")
                    st.progress(int(rsi))

# ==========================================
# ABA 2: TESOURO DIRETO
# ==========================================
with aba_tesouro:
    st.subheader("Visão de Renda Fixa")
    
    # --- CARTEIRA FAMÍLIA ---
    st.markdown("### 👨‍👩‍👧‍👦 Família - Meta 500k")
    
    dados_familia = {
        "Ativo": ["IPCA+ 2032", "PRÉ 2032", "Selic 2031", "TOTAL FAMÍLIA"],
        "Investido (R$)": [2987.73, 999.32, 96038.86, 101173.41],
        "Posição Atual (R$)": [3234.00, 1078.00, 100821.00, 105133.00],
        "Ganho (R$)": [246.27, 78.68, 4782.14, 5107.09],
        "Rentabilidade (%)": [8.24, 7.87, 4.98, 5.05]
    }
    df_familia = pd.DataFrame(dados_familia)
    
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
        st.metric(label="Falta para a Meta (R$ 500.000)", value="R$ 394.867,00")
    with col_meta2:
        st.metric(label="Progresso da Meta", value="21.0%")
    
    st.divider()

    # --- CARTEIRA MARIA ---
    st.markdown("### 👩 Maria Invest")
    
    dados_maria = {
        "Ativo": ["IPCA+ 2029", "IPCA+ 2032", "IPCA+ 2035 c/juros", "PRÉ 2032", "PRÉ 2035 c/juros", "SELIC 2031", "TOTAL MARIA"],
        "Investido (R$)": [5779.67, 1580.87, 5444.10, 956.39, 2370.30, 26095.77, 42227.10],
        "Posição Atual (R$)": [6643.00, 1710.00, 5953.00, 1080.00, 2498.00, 29448.00, 47332.00],
        "Ganho (R$)": [863.33, 129.13, 508.90, 123.61, 127.70, 3352.23, 5104.90],
        "Rentabilidade (%)": [14.94, 8.17, 9.35, 12.92, 5.39, 12.85, 12.09]
    }
    df_maria = pd.DataFrame(dados_maria)
    
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
    col_res1.metric("Total Investido", "R$ 144.548,01")
    col_res2.metric("Posição Atual", "R$ 153.595,41")
    col_res3.metric("Rentabilidade Global", "6.26%")