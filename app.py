import streamlit as st
import yfinance as yf
import pandas as pd
import extra_streamlit_components as stx
import hashlib
from datetime import datetime, timedelta
import numpy as np 

# 1. Configuração da Página
st.set_page_config(page_title="DinDin", page_icon="💰", layout="wide")

# --- CSS PARA REMOVER ESPAÇOS DO TOPO E DO HEADER ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
        header { visibility: hidden; }
        .header-container { display: flex; justify-content: space-between; align-items: flex-end; margin-top: -30px; margin-bottom: 15px; }
        .header-title { font-size: 2.2rem; font-weight: 700; margin: 0; line-height: 1; }
        .header-subtitle { font-size: 0.9rem; color: #888; margin-top: 5px; }
        .kpi-box { text-align: left; }
        .kpi-label { font-size: 0.8rem; color: #888; margin-bottom: 3px; }
        .kpi-value { font-size: 1.4rem; font-weight: 600; line-height: 1; }
        .kpi-sub { font-size: 0.8rem; margin-top: 3px; font-weight: bold; }
        .kpi-meta { text-align: right; }
    </style>
""", unsafe_allow_html=True)

# Inicializa o gerenciador de cookies
cookie_manager = stx.CookieManager(key="cookie_dindin")

# ==========================================
# 2. TRAVA DE SEGURANÇA (COM COOKIES)
# ==========================================
token_seguranca = hashlib.sha256(st.secrets["app_password"].encode()).hexdigest()

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

auth_cookie = cookie_manager.get(cookie="dindin_auth")

if not st.session_state.password_correct and auth_cookie == token_seguranca:
    st.session_state.password_correct = True

if not st.session_state.password_correct:
    st.title("🔒 Acesso Restrito")
    st.write("Este aplicativo é privado. Insira a senha para visualizar os investimentos.")
    password = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if password == st.secrets["app_password"]:
            st.session_state.password_correct = True
            cookie_manager.set("dindin_auth", token_seguranca, expires_at=datetime.now() + timedelta(days=7))
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
    st.stop() 

with st.sidebar:
    st.write("---")
    if st.button("Sair do App"):
        cookie_manager.delete("dindin_auth")
        st.session_state.password_correct = False
        st.rerun()

# ==========================================
# FUNÇÕES E DICIONÁRIOS DE APOIO
# ==========================================
def fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Função para formatar a data do mínimo em (mês/ano)
def formatar_data_min(data_timestamp):
    if pd.isna(data_timestamp):
        return ""
    meses_pt = {
        'Jan': 'jan', 'Feb': 'fev', 'Mar': 'mar', 'Apr': 'abr', 
        'May': 'mai', 'Jun': 'jun', 'Jul': 'jul', 'Aug': 'ago', 
        'Sep': 'set', 'Oct': 'out', 'Nov': 'nov', 'Dec': 'dez'
    }
    mes = meses_pt.get(data_timestamp.strftime('%b'), data_timestamp.strftime('%b').lower())
    ano = data_timestamp.strftime('%y')
    return f" ({mes}/{ano})"

# Função para pintar taxas negativas de vermelho
def style_taxa(val):
    color = '#FF4B4B' if val < 0 else '#FAFAFA' # Vermelho para negativo, branco para positivo
    return f'color: {color}; font-weight: bold;'

dicionario_empresas = {
    'VALE3': 'Vale S.A. (Mineração)', 'WEGE3': 'WEG S.A. (Motores)', 
    'ITSA4': 'Itaúsa (Holding)', 'BOVA11': 'iShares (ETF Ibov)', 
    'CEAB3': 'C&A Modas (Varejo)', 'XPML11': 'XP Malls (FII Shoppings)', 
    'MCCI11': 'Mauá Capital (FII Papel)', 'PETR4': 'Petrobras (Petróleo)', 
    'BBAS3': 'Banco do Brasil (Banco)', 'ITUB4': 'Itaú Unibanco (Banco)', 
    'BBDC4': 'Bradesco (Banco)', 'MGLU3': 'Magazine Luiza (Varejo)', 
    'LREN3': 'Lojas Renner (Varejo)', 'VIVT3': 'Telefônica Vivo (Telecom)', 
    'TAEE11': 'Taesa (Energia)', 'KLBN11': 'Klabin (Papel/Celulose)', 
    'SANB11': 'Santander (Banco)', 'BPAC11': 'BTG Pactual (Banco)', 
    'HGLG11': 'CSHG Logística (FII)', 'KNRI11': 'Kinea Renda (FII Híbrido)', 
    'MXRF11': 'Maxi Renda (FII Papel)'
}

@st.cache_data(ttl=900)
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

def gerar_tabela_renda_fixa(ativos, investidos, posicoes, ganhos, taxas_atuais):
    df = pd.DataFrame({
        "Ativo": ativos,
        "Investido (R$)": investidos,
        "Posição Atual (R$)": posicoes,
        "Ganho (R$)": ganhos,
        "Taxa (%)": taxas_atuais
    })
    
    meses_2026 = ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]
    dados_grafico = {}
    
    for mes in meses_2026:
        df[mes] = [0.0] * len(ativos)
        df[f"Tx {mes}"] = [0.0] * len(ativos)

    for i, ativo in enumerate(ativos):
        if "PRÉ" in ativo:
            base_rate = 12.5
        elif "Selic" in ativo:
            base_rate = 11.0
        else:
            base_rate = 6.5
        
        taxas_ativo = []
        
        for j, mes in enumerate(meses_2026):
            taxa_ano = base_rate + np.random.uniform(-0.8, 0.8)
            taxas_ativo.append(taxa_ano)
            
            taxa_mensal = (1 + (taxa_ano / 100)) ** (1/12) - 1
            fator = (1 + taxa_mensal) ** (j + 1)
            
            df.loc[df.index[i], mes] = posicoes[i] * fator
            df.loc[df.index[i], f"Tx {mes}"] = taxa_ano
            
        dados_grafico[ativo] = taxas_ativo
        
    df_grafico = pd.DataFrame(dados_grafico, index=meses_2026)
    return df, df_grafico

# ==========================================
# CABEÇALHO COMPACTO
# ==========================================
inv_geral = st.secrets["familia"]["investido"][-1]
pos_geral = st.secrets["familia"]["posicao"][-1]
rent_geral = st.secrets["familia"]["rentabilidade"][-1]

inv_rv = sum(st.secrets["renda_variavel"].get("investido_renda_variavel", []))
pos_rv = st.secrets["renda_variavel"].get("total_posicao", 0.0)
rent_rv = st.secrets["renda_variavel"].get("total_rentabilidade", 0.0)

inv_rf = sum(st.secrets["familia"]["investido"][:-1])
ganho_rf = sum(st.secrets["familia"]["ganho"][:-1])
rent_rf = (ganho_rf / inv_rf) * 100 if inv_rf > 0 else 0

cor_rv = "#00FF00" if rent_rv >= 0 else "#FF4B4B"

header_html = f"""
<div class="header-container">
<div style="flex: 2;">
<div class="header-title">💰 DinDin</div>
<div class="header-subtitle">Seus investimentos e dicas em um só lugar.</div>
</div>
<div class="kpi-box" style="flex: 1;">
<div class="kpi-label">Total Investido</div>
<div class="kpi-value">{fmt_brl(inv_geral)}</div>
</div>
<div class="kpi-box" style="flex: 1;">
<div class="kpi-label">Posição Atual</div>
<div class="kpi-value">{fmt_brl(pos_geral)}</div>
</div>
<div class="kpi-box" style="flex: 0.8;">
<div class="kpi-label">Rentab.</div>
<div class="kpi-value" style="color: #00FF00;">{rent_geral:.2f}%</div>
</div>
<div class="kpi-box" style="flex: 1.2;">
<div class="kpi-label">Total Variável</div>
<div class="kpi-value">{fmt_brl(inv_rv)}</div>
<div class="kpi-sub" style="color: {cor_rv};">{rent_rv:.2f}%</div>
</div>
<div class="kpi-box" style="flex: 1.2;">
<div class="kpi-label">Total Fixo</div>
<div class="kpi-value">{fmt_brl(inv_rf)}</div>
<div class="kpi-sub" style="color: #00FF00;">{rent_rf:.2f}%</div>
</div>
<div class="kpi-meta" style="flex: 1.5;">
<div class="kpi-label">Meta 500k ({st.secrets['familia']['meta_progresso']})</div>
<div class="kpi-value" style="font-size: 1.2rem;">Atual: {st.secrets['familia']['meta_falta']}</div>
</div>
</div>
<hr style="margin: 0px 0 15px 0; border: 0; border-top: 1px solid #333;">
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# CRIANDO AS 3 ABAS
# ==========================================
aba_renda_variavel, aba_renda_fixa, aba_maria = st.tabs([
    "📈 Renda Variável (Ações e FIIs)", 
    "🏦 Renda Fixa", 
    "👩 Invest Maria"
])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Sua Carteira de Cotações")
    
    carteira_acoes = st.secrets["renda_variavel"]["carteira_acoes"]
    inv_ativos = st.secrets["renda_variavel"].get("investido_renda_variavel", [])
    
    total_investido_rv = sum(inv_ativos) if inv_ativos else 0
    ganho_rv_real = st.secrets["renda_variavel"].get("total_ganho", 0.0)
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Investido", fmt_brl(total_investido_rv))
        c2.metric("Posição Atual", fmt_brl(pos_rv))
        c3.metric("Ganho Total", fmt_brl(ganho_rv_real))
        c4.metric("Rentabilidade Média", f"{rent_rv:.2f}%")
    
    st.write("")
    
    cols = st.columns(len(carteira_acoes))

    for i, ativo in enumerate(carteira_acoes):
        hist = buscar_dados(ativo)
        
        if not hist.empty:
            preco_atual = hist['Close'].iloc[-1]
            preco_anterior = hist['Close'].iloc[-2]
            variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
            rsi = calcular_rsi(hist['Close'])
            
            min_6m = hist['Low'].tail(126).min()
            
            hist_5a = hist['Low'].tail(1260)
            min_5a = hist_5a.min()
            data_min_5a = hist_5a.idxmin()
            texto_data_5a = formatar_data_min(data_min_5a)
            
            share = (inv_ativos[i] / total_investido_rv) * 100 if total_investido_rv > 0 and i < len(inv_ativos) else 0
                
            sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
            cor = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                
            nome_empresa = dicionario_empresas.get(ativo, "")
                
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><span style='font-size: 16px; font-weight: bold; color: white;'>{ativo}</span><br><span style='font-size: 10px; color: #888;'>{nome_empresa}</span></div>", unsafe_allow_html=True)
                    
                    st.metric(label="Cotação Atual", value=f"R$ {preco_atual:.2f}", delta=f"{variacao_pct:.2f}%", label_visibility="collapsed")
                    
                    st.markdown(f"<div style='font-size: 12px; line-height: 1.3; margin-top: -10px; margin-bottom: 5px;'>📉 <b>Mín 6m:</b> R$ {min_6m:.2f}<br>⏳ <b>Mín 5a:</b> R$ {min_5a:.2f}{texto_data_5a}<br>📊 <b>RSI:</b> {rsi:.1f}<br>🤖 <b>Sinal:</b> <span style='color:{cor}; font-weight: bold;'>{sinal}</span><br>💼 <b>Share:</b> {share:.1f}%</div>", unsafe_allow_html=True)
                    
                    st.progress(share / 100.0) 

    st.divider()

    st.subheader("🔥 Oportunidades de Compra (Radar)")
    st.markdown("Ativos com RSI abaixo de 35 (Sobrevendidos) no mercado agora:")

    radar_tickers = ['PETR4', 'BBAS3', 'ITUB4', 'BBDC4', 'MGLU3', 'LREN3', 'VIVT3', 'TAEE11', 'KLBN11', 'SANB11', 'BPAC11', 'HGLG11', 'KNRI11', 'MXRF11']
    oportunidades = []

    for ticker in radar_tickers:
        hist_radar = buscar_dados(ticker)
        if not hist_radar.empty:
            rsi_radar = calcular_rsi(hist_radar['Close'])
            if rsi_radar < 35:
                preco_radar = hist_radar['Close'].iloc[-1]
                preco_ant_radar = hist_radar['Close'].iloc[-2]
                var_pct_radar = ((preco_radar - preco_ant_radar) / preco_ant_radar) * 100
                min_6m_radar = hist_radar['Low'].tail(126).min()
                
                hist_radar_5a = hist_radar['Low'].tail(1260)
                min_5a_radar = hist_radar_5a.min()
                data_min_5a_radar = hist_radar_5a.idxmin()
                texto_data_5a_radar = formatar_data_min(data_min_5a_radar)
                
                oportunidades.append({
                    "ativo": ticker, "preco": preco_radar, "variacao": var_pct_radar,
                    "rsi": rsi_radar, "min_6m": min_6m_radar, "min_5a": min_5a_radar,
                    "data_min_5a": texto_data_5a_radar
                })

    if oportunidades:
        cols_op = st.columns(len(carteira_acoes)) 
        for i, op in enumerate(oportunidades):
            nome_empresa_radar = dicionario_empresas.get(op['ativo'], "")
            with cols_op[i % len(cols_op)]:
                with st.container(border=True):
                    st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><span style='font-size: 16px; font-weight: bold; color: #00FF00;'>{op['ativo']}</span><br><span style='font-size: 10px; color: #888;'>{nome_empresa_radar}</span></div>", unsafe_allow_html=True)
                    
                    st.metric(label="Preço", value=f"R$ {op['preco']:.2f}", delta=f"{op['variacao']:.2f}%", label_visibility="collapsed")
                    
                    st.markdown(f"<div style='font-size: 12px; line-height: 1.3; margin-top: -10px; margin-bottom: 5px;'>🎯 <b>RSI:</b> {op['rsi']:.1f}<br>📉 <b>Mín 6m:</b> R$ {op['min_6m']:.2f}<br>⏳ <b>Mín 5a:</b> R$ {op['min_5a']:.2f}{op['data_min_5a']}</div>", unsafe_allow_html=True)
    else:
        st.info("Nenhuma oportunidade no radar no momento.")

# ==========================================
# ABA 2: RENDA FIXA (FAMÍLIA)
# ==========================================
with aba_renda_fixa:
    st.subheader("Painel de Renda Fixa")
    
    ativos_fam = st.secrets["familia"]["ativos"][:-1]
    inv_fam = st.secrets["familia"]["investido"][:-1]
    pos_fam = st.secrets["familia"]["posicao"][:-1]
    gan_fam = st.secrets["familia"]["ganho"][:-1]
    rent_fam = st.secrets["familia"]["rentabilidade"][:-1]
    
    total_investido = sum(inv_fam)
    total_posicao = sum(pos_fam)
    total_ganho = sum(gan_fam)
    rent_media = (total_ganho / total_investido) * 100 if total_investido > 0 else 0

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Investido", fmt_brl(total_investido))
        c2.metric("Posição Atual", fmt_brl(total_posicao))
        c3.metric("Ganho Total", fmt_brl(total_ganho))
        c4.metric("Rentabilidade Média", f"{rent_media:.2f}%")

    st.write("")
    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_fam, df_grafico_fam = gerar_tabela_renda_fixa(ativos_fam, inv_fam, pos_fam, gan_fam, rent_fam)
    
    # Insere a coluna Share (%) logo após Taxa (%)
    df_fam.insert(5, "Share (%)", (df_fam["Investido (R$)"] / total_investido) * 100)

    # Aplica a cor vermelha nas taxas negativas e a borda de separação
    styled_fam = df_fam.style.map(style_taxa, subset=['Taxa (%)'])
    styled_fam = styled_fam.set_properties(subset=['Share (%)'], **{'border-right': '2px solid #555'})

    config_colunas = {
        "Investido (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Posição Atual (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Ganho (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
        "Taxa (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "Share (%)": st.column_config.ProgressColumn("Share (%)", format="%.1f%%", min_value=0, max_value=100)
    }
    
    meses = ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]
    for mes in meses:
        config_colunas[mes] = st.column_config.NumberColumn(format="R$ %.2f")
        config_colunas[f"Tx {mes}"] = st.column_config.NumberColumn(format="%.2f%%")

    st.dataframe(styled_fam, hide_index=True, use_container_width=True, column_config=config_colunas)

    st.write("")
    st.markdown("#### Evolução das Taxas - Família (2026)")
    st.line_chart(df_grafico_fam, height=300)

# ==========================================
# ABA 3: INVEST MARIA
# ==========================================
with aba_maria:
    st.subheader("Painel de Renda Fixa - Maria")
    
    ativos_maria = st.secrets["maria"]["ativos"][:-1]
    inv_maria = st.secrets["maria"]["investido"][:-1]
    pos_maria = st.secrets["maria"]["posicao"][:-1]
    gan_maria = st.secrets["maria"]["ganho"][:-1]
    rent_maria = st.secrets["maria"]["rentabilidade"][:-1]
    
    total_investido_maria = sum(inv_maria)
    total_posicao_maria = sum(pos_maria)
    total_ganho_maria = sum(gan_maria)
    rent_media_maria = (total_ganho_maria / total_investido_maria) * 100 if total_investido_maria > 0 else 0

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Investido", fmt_brl(total_investido_maria))
        c2.metric("Posição Atual", fmt_brl(total_posicao_maria))
        c3.metric("Ganho Total", fmt_brl(total_ganho_maria))
        c4.metric("Rentabilidade Média", f"{rent_media_maria:.2f}%")

    st.write("")
    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_maria, df_grafico_maria = gerar_tabela_renda_fixa(ativos_maria, inv_maria, pos_maria, gan_maria, rent_maria)
    
    # Insere a coluna Share (%) logo após Taxa (%)
    df_maria.insert(5, "Share (%)", (df_maria["Investido (R$)"] / total_investido_maria) * 100)

    # Aplica a cor vermelha nas taxas negativas e a borda de separação
    styled_maria = df_maria.style.map(style_taxa, subset=['Taxa (%)'])
    styled_maria = styled_maria.set_properties(subset=['Share (%)'], **{'border-right': '2px solid #555'})

    st.dataframe(styled_maria, hide_index=True, use_container_width=True, column_config=config_colunas)

    st.write("")
    st.markdown("#### Evolução das Taxas - Maria (2026)")
    st.line_chart(df_grafico_maria, height=300)