import streamlit as st
import yfinance as yf
import pandas as pd
import extra_streamlit_components as stx
import hashlib
from datetime import datetime, timedelta
import numpy as np 
import math
import altair as alt 
import requests 

# 1. Configuração da Página
st.set_page_config(page_title="DinDin", page_icon="💰", layout="wide")

# --- CSS PARA REMOVER ESPAÇOS DO TOPO E DO HEADER ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
        header { visibility: hidden; }
        
        .header-container { 
            display: flex; flex-wrap: wrap; gap: 15px; justify-content: space-between; align-items: flex-end; 
            margin-top: -30px; margin-bottom: 15px;
        }
        .header-title { font-size: 2.2rem; font-weight: 700; margin: 0; line-height: 1; }
        .header-subtitle { font-size: 0.9rem; color: #888; margin-top: 5px; }
        .kpi-box { text-align: left; flex: 1; min-width: 100px; }
        .kpi-label { font-size: 0.8rem; color: #888; margin-bottom: 3px; }
        .kpi-value { font-size: 1.4rem; font-weight: 600; line-height: 1; }
        .kpi-sub { font-size: 0.8rem; margin-top: 3px; font-weight: bold; }
        .kpi-meta { text-align: right; flex: 1.5; min-width: 150px; }
        
        .compact-list { margin-top: 0px; margin-bottom: 0px; padding-left: 20px; line-height: 1.4; font-size: 13px; }
        .compact-list li { margin-bottom: 4px; }
        .news-link { color: #4da6ff; text-decoration: none; font-size: 11px; margin-left: 5px; }
        .news-link:hover { text-decoration: underline; }
        a.ticker-link { text-decoration: none; }
        a.ticker-link:hover { text-decoration: underline; }

        /* REDUZIR AINDA MAIS A LARGURA E PADDING DOS CARDS DE AÇÕES */
        div[data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"] {
            max-width: 200px !important; margin: 0 auto !important; padding: 8px !important;
        }
        div[data-testid="column"] div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
        div[data-testid="column"] div[data-testid="stMarkdownContainer"] p { font-size: 11px !important; }
    </style>
""", unsafe_allow_html=True)

cookie_manager = stx.CookieManager(key="cookie_dindin")
token_seguranca = hashlib.sha256(st.secrets["app_password"].encode()).hexdigest()

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False
auth_cookie = cookie_manager.get(cookie="dindin_auth")
if not st.session_state.password_correct and auth_cookie == token_seguranca:
    st.session_state.password_correct = True

if not st.session_state.password_correct:
    st.title("🔒 Acesso Restrito")
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
    if st.button("Sair do App"):
        cookie_manager.delete("dindin_auth")
        st.session_state.password_correct = False
        st.rerun()

# ==========================================
# FUNÇÕES E DICIONÁRIOS DE APOIO
# ==========================================
def fmt_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_pct(valor):
    return f"{valor:.2f}%".replace(".", ",")

# NOVA FUNÇÃO: Formata valores grandes (ex: 5.900.000.000 -> R$ 5,9 Bi)
def fmt_grande(valor):
    if valor is None: return ""
    try:
        if abs(valor) >= 1e9: return f"R$ {valor/1e9:.1f} Bi".replace(".", ",")
        if abs(valor) >= 1e6: return f"R$ {valor/1e6:.1f} Mi".replace(".", ",")
        return fmt_brl(valor)
    except:
        return str(valor)

def gerar_link_investidor10(ticker):
    ticker_lower = ticker.lower()
    if ticker_lower in ['xpml11', 'mcci11', 'hglg11', 'knri11', 'mxrf11']:
        return f"https://investidor10.com.br/fiis/{ticker_lower}/"
    elif ticker_lower in ['bova11']:
        return f"https://investidor10.com.br/etfs/{ticker_lower}/"
    else:
        return f"https://investidor10.com.br/acoes/{ticker_lower}/"

def formatar_data_min(data_timestamp):
    if pd.isna(data_timestamp): return ""
    meses_pt = {'Jan': 'jan', 'Feb': 'fev', 'Mar': 'mar', 'Apr': 'abr', 'May': 'mai', 'Jun': 'jun', 'Jul': 'jul', 'Aug': 'ago', 'Sep': 'set', 'Oct': 'out', 'Nov': 'nov', 'Dec': 'dez'}
    return f" ({meses_pt.get(data_timestamp.strftime('%b'), '')}/{data_timestamp.strftime('%y')})"

def style_taxa(val):
    return f'color: {"#FF4B4B" if val < 0 else "#FAFAFA"}; font-weight: bold;'

# --- NOVA FUNÇÃO CONSOLIDADA: DADOSB3 ---
@st.cache_data(ttl=86400) 
def buscar_metricas_fundamentalistas(ticker):
    try:
        api_key = st.secrets["api_keys"]["dadosb3"]
    except KeyError:
        return {}
        
    headers = {"X-API-Key": api_key}
    metricas = {"score": 0, "roe": None, "receita": None, "divida": None}

    # 1. Busca Faturamento (Receita) e Dívida Líquida (Balanços/Resultados)
    try:
        res_bal = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/balancos", headers=headers, timeout=5)
        if res_bal.status_code == 200:
            periodos = res_bal.json().get("periodos", [])
            if periodos:
                ultimo = periodos[-1]
                # Tenta receita_liquida ou apenas receita
                metricas["receita"] = ultimo.get("receita_liquida") or ultimo.get("receita")
                metricas["divida"] = ultimo.get("divida_liquida")
    except:
        pass

    # 2. Busca ROE e Dívida/EBITDA (Indicadores)
    try:
        res_ind = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/indicadores", headers=headers, timeout=5)
        if res_ind.status_code == 200:
            anos = res_ind.json().get("anos", [])
            if anos:
                ultimo_ano = anos[-1]
                roe = ultimo_ano.get("roe")
                div_ebitda = ultimo_ano.get("divida_liquida_ebitda", 10)
                metricas["roe"] = roe
                
                if roe and roe > 15: metricas["score"] += 2
                if div_ebitda and div_ebitda < 2.5: metricas["score"] += 1
    except:
        pass

    # 3. Busca P/L (Múltiplos)
    try:
        res_mult = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/multiplos", headers=headers, timeout=5)
        if res_mult.status_code == 200:
            pl = res_mult.json().get("pl")
            if pl and 0 < pl < 15: metricas["score"] += 1
    except:
        pass

    return metricas

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
    return 100 - (100 / (1 + rs.iloc[-1]))

def gerar_tabela_renda_fixa(ativos, investidos, posicoes, ganhos, taxas_atuais):
    df = pd.DataFrame({"Ativo": ativos, "Investido (R$)": investidos, "Posição Atual (R$)": posicoes, "Ganho (R$)": ganhos, "Taxa (%)": taxas_atuais})
    meses_2026 = ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]
    dados_grafico = {}
    for mes in meses_2026: df[mes] = [0.0] * len(ativos); df[f"Tx {mes}"] = [0.0] * len(ativos)
    meses_grafico = meses_2026[:10]
    for i, ativo in enumerate(ativos):
        base_rate = 12.5 if "PRÉ" in ativo else (11.0 if "Selic" in ativo else 6.5)
        taxas_ativo = []
        for j, mes in enumerate(meses_2026):
            taxa_ano = base_rate + np.random.uniform(-0.8, 0.8)
            df.loc[df.index[i], mes] = posicoes[i] * ((1 + ((1 + (taxa_ano / 100)) ** (1/12) - 1)) ** (j + 1))
            df.loc[df.index[i], f"Tx {mes}"] = taxa_ano
            if j < 10: taxas_ativo.append(taxa_ano)
        dados_grafico[ativo] = taxas_ativo
    df_grafico = pd.DataFrame(dados_grafico, index=[m.split('/')[0] for m in meses_grafico])
    return df, df_grafico

# (Funções de Notícias mantidas iguais...)
def get_noticias_renda_variavel(): return """<ul class="compact-list"><li><b>VALE3:</b> Ação sobe forte após 'call' positiva. <a class="news-link" href="#">[Ler mais]</a></li></ul>"""
def get_oportunidades_renda_variavel(): return """<ul class="compact-list"><li><b>Small Caps:</b> BB-BI inclui PINE4. <a class="news-link" href="#">[Ler mais]</a></li></ul>"""
def get_noticias_renda_fixa(titulos): return "<ul class='compact-list'><li><b>Tesouro Direto:</b> Acompanhe as taxas hoje. <a class='news-link' href='#'>[Ler mais]</a></li></ul>"
def get_oportunidades_renda_fixa(): return """<ul class="compact-list"><li><b>IPCA+:</b> Juro real volta a 8%. <a class="news-link" href="#">[Ler mais]</a></li></ul>"""

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
<div class="header-container" id="topo">
<div style="flex: 2; min-width: 200px;"><div class="header-title"><a href="#topo" target="_self" style="text-decoration: none; color: inherit;">💰 DinDin</a></div><div class="header-subtitle">Seus investimentos e dicas em um só lugar.</div></div>
<div class="kpi-box"><div class="kpi-label">Total Investido</div><div class="kpi-value">{fmt_brl(inv_geral)}</div></div>
<div class="kpi-box"><div class="kpi-label">Posição Atual</div><div class="kpi-value">{fmt_brl(pos_geral)}</div></div>
<div class="kpi-box" style="flex: 0.8;"><div class="kpi-label">Rentab.</div><div class="kpi-value" style="color: #00FF00;">{fmt_pct(rent_geral)}</div></div>
<div class="kpi-box" style="flex: 1.2;"><div class="kpi-label">Total Variável</div><div class="kpi-value">{fmt_brl(inv_rv)}</div><div class="kpi-sub" style="color: {cor_rv};">{fmt_pct(rent_rv)}</div></div>
<div class="kpi-box" style="flex: 1.2;"><div class="kpi-label">Total Fixo</div><div class="kpi-value">{fmt_brl(inv_rf)}</div><div class="kpi-sub" style="color: #00FF00;">{fmt_pct(rent_rf)}</div></div>
<div class="kpi-meta"><div class="kpi-label">Meta 500k ({st.secrets['familia']['meta_progresso']})</div><div class="kpi-value" style="font-size: 1.2rem;">Atual: {st.secrets['familia']['meta_falta']}</div></div>
</div>
<hr style="margin: 0px 0 15px 0; border: 0; border-top: 1px solid #333;">
"""
st.markdown(header_html, unsafe_allow_html=True)

# ==========================================
# CRIANDO AS 3 ABAS
# ==========================================
aba_renda_variavel, aba_renda_fixa, aba_maria = st.tabs(["📈 Renda Variável (Ações e FIIs)", "🏦 Renda Fixa", "👩 Invest Maria"])

# ==========================================
# ABA 1: RENDA VARIÁVEL
# ==========================================
with aba_renda_variavel:
    st.subheader("Sua Carteira de Cotações")
    carteira_acoes = st.secrets["renda_variavel"]["carteira_acoes"]
    inv_ativos = st.secrets["renda_variavel"].get("investido_renda_variavel", [])
    total_investido_rv = sum(inv_ativos) if inv_ativos else 0
    
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Investido", fmt_brl(total_investido_rv)); c2.metric("Posição Atual", fmt_brl(pos_rv))
        c3.metric("Ganho Total", fmt_brl(st.secrets["renda_variavel"].get("total_ganho", 0.0))); c4.metric("Rentabilidade Média", fmt_pct(rent_rv))
    
    st.write("")
    num_cols = 4
    for row in range(math.ceil(len(carteira_acoes) / num_cols)):
        cols = st.columns(num_cols)
        for i in range(num_cols):
            idx = row * num_cols + i
            if idx < len(carteira_acoes):
                ativo = carteira_acoes[idx]
                hist = buscar_dados(ativo)
                if not hist.empty:
                    preco_atual = hist['Close'].iloc[-1]; preco_anterior = hist['Close'].iloc[-2]
                    variacao_pct = ((preco_atual - preco_anterior) / preco_anterior) * 100
                    rsi = calcular_rsi(hist['Close'])
                    min_6m = hist['Low'].tail(126).min()
                    hist_5a = hist['Low'].tail(1260); min_5a = hist_5a.min()
                    texto_data_5a = formatar_data_min(hist_5a.idxmin())
                    share = (inv_ativos[idx] / total_investido_rv) * 100 if total_investido_rv > 0 and idx < len(inv_ativos) else 0
                    sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
                    cor = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                    nome_empresa = dicionario_empresas.get(ativo, "")
                    link = gerar_link_investidor10(ativo)
                    
                    # Busca as métricas fundamentalistas
                    metricas = buscar_metricas_fundamentalistas(ativo)
                        
                    with cols[i]:
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link}' target='_blank' style='font-size: 16px; font-weight: bold; color: white;'>{ativo}</a><br><span style='font-size: 10px; color: #888;'>{nome_empresa}</span></div>", unsafe_allow_html=True)
                            st.metric(label="Cotação Atual", value=fmt_brl(preco_atual), delta=f"{variacao_pct:.2f}%".replace(".", ","), label_visibility="collapsed")
                            
                            # Bloco de dados técnicos
                            html_tecnico = f"<div style='font-size: 12px; line-height: 1.3; margin-top: -10px; margin-bottom: 5px;'>📉 <b>Mín 6m:</b> {fmt_brl(min_6m)}<br>⏳ <b>Mín 5a:</b> {fmt_brl(min_5a)}{texto_data_5a}<br>📊 <b>RSI:</b> {rsi:.1f}".replace(".", ",") + f"<br>🤖 <b>Sinal:</b> <span style='color:{cor}; font-weight: bold;'>{sinal}</span><br>💼 <b>Share:</b> {share:.1f}%".replace(".", ",") + "</div>"
                            st.markdown(html_tecnico, unsafe_allow_html=True)
                            
                            # Bloco de indicadores fundamentalistas (ÚNICO MARKDOWN)
                            html_indicadores = ""
                            if metricas.get("receita") or metricas.get("divida") or metricas.get("roe"):
                                html_indicadores += "<hr style='margin: 5px 0; border-top: 1px solid #444;'>"
                                if metricas.get("receita"): html_indicadores += f"<div style='font-size: 11px; color: #ddd;'>💰 <b>Receita:</b> {fmt_grande(metricas['receita'])}</div>"
                                if metricas.get("divida"): html_indicadores += f"<div style='font-size: 11px; color: #ddd;'>🏦 <b>Dív. Líq:</b> {fmt_grande(metricas['divida'])}</div>"
                                if metricas.get("roe"): html_indicadores += f"<div style='font-size: 11px; color: #ddd;'>🏆 <b>ROE:</b> {fmt_pct(metricas['roe'])}</div>"
                                st.markdown(html_indicadores, unsafe_allow_html=True)
                            
                            st.progress(share / 100.0) 

    # ... RESTANTE DO CÓDIGO (RADAR, RENDA FIXA, MARIA) ...
    # (Mantido idêntico ao seu arquivo original para focar na correção dos cards)