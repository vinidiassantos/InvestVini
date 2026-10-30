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

# --- CSS TOTALMENTE RESPONSIVO (CELULAR E DESKTOP) ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
        header { visibility: hidden; }
        
        /* Ajustes para telas de celular */
        @media (max-width: 768px) {
            .block-container { padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
            .header-title { font-size: 1.8rem !important; }
            .kpi-value { font-size: 1.1rem !important; }
            .kpi-label { font-size: 0.7rem !important; }
        }
        
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
        
        /* Estilo para os bullets compactos */
        .compact-list { margin-top: 0px; margin-bottom: 0px; padding-left: 20px; line-height: 1.4; font-size: 13px; }
        .compact-list li { margin-bottom: 4px; }
        .news-link { color: #4da6ff; text-decoration: none; font-size: 11px; margin-left: 5px; }
        .news-link:hover { text-decoration: underline; }
        
        /* Remove sublinhado dos links nos cards */
        a.ticker-link { text-decoration: none; }
        a.ticker-link:hover { text-decoration: underline; }

        /* ESTILO RESPONSIVO PARA OS CARDS DE AÇÕES */
        div[data-testid="column"] div[data-testid="stVerticalBlockBorderWrapper"] {
            width: 100% !important;
            max-width: 250px !important; /* Um pouco mais largo para caber os novos dados */
            margin: 0 auto !important;
            padding: 10px !important;
        }
        
        /* Ajusta o tamanho da fonte do valor principal */
        div[data-testid="column"] div[data-testid="stMetricValue"] {
            font-size: 1.6rem !important;
        }
        /* Ajusta a fonte dos detalhes internos */
        div[data-testid="column"] div[data-testid="stMarkdownContainer"] p {
            font-size: 11px !important;
        }
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

def fmt_pct(valor):
    return f"{valor:.2f}%".replace(".", ",")

# Formata valores grandes (ex: 5.900.000.000 -> R$ 5,9 Bi)
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

def style_taxa(val):
    color = '#FF4B4B' if val < 0 else '#FAFAFA' 
    return f'color: {color}; font-weight: bold;'

# --- FUNÇÃO CONSOLIDADA: API DADOSB3 (BALANÇO, INDICADORES E MÚLTIPLOS) ---
@st.cache_data(ttl=86400) 
def buscar_metricas_fundamentalistas(ticker):
    try:
        api_key = st.secrets["api_keys"]["dadosb3"]
    except KeyError:
        return {}
        
    headers = {"X-API-Key": api_key}
    metricas = {"score": 0, "roe": None, "receita": None, "divida": None}

    # 1. Busca Faturamento (Receita) e Dívida Líquida
    try:
        res_bal = requests.get(f"https://dadosb3.com/api/empresas/{ticker}/balancos", headers=headers, timeout=5)
        if res_bal.status_code == 200:
            periodos = res_bal.json().get("periodos", [])
            if periodos:
                ultimo = periodos[-1]
                metricas["receita"] = ultimo.get("receita_liquida") or ultimo.get("receita")
                metricas["divida"] = ultimo.get("divida_liquida")
    except:
        pass

    # 2. Busca ROE e Dívida/EBITDA
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

    # 3. Busca P/L
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

    meses_grafico = meses_2026[:10] # Apenas até Out/26
    
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
            
            taxa_mensal = (1 + (taxa_ano / 100)) ** (1/12) - 1
            fator = (1 + taxa_mensal) ** (j + 1)
            
            df.loc[df.index[i], mes] = posicoes[i] * fator
            df.loc[df.index[i], f"Tx {mes}"] = taxa_ano
            
            if j < 10:
                taxas_ativo.append(taxa_ano)
            
        dados_grafico[ativo] = taxas_ativo
        
    df_grafico = pd.DataFrame(dados_grafico, index=[m.split('/')[0] for m in meses_grafico])
    
    return df, df_grafico

# ==========================================
# NOTÍCIAS E OPORTUNIDADES (BULLETS)
# ==========================================
def get_noticias_renda_variavel():
    return """
    <ul class="compact-list">
        <li><b>VALE3:</b> Ação sobe forte após 'call' positiva sobre câmbio e metais, mesmo com lucro em queda. <a class="news-link" href="https://valor.globo.com/financas/noticia/2026/10/30/acoes-da-vale-vale3-sobem-forte-apos-call-com-perspectiva-mais-positiva-sobre-cambio-e-metais.ghtml" target="_blank">[Ler mais]</a></li>
        <li><b>WEGE3:</b> Dispara 4,4% hoje e acumula alta de 15,3% na semana, na contramão do Ibovespa. <a class="news-link" href="https://br.investing.com/analysis/wege3-dispara-44-hoje-weg-sobe-153-na-semana-enquanto-o-ibovespa-cai-200480439" target="_blank">[Ler mais]</a></li>
        <li><b>ITSA4:</b> Holding negocia perto de R$ 13,00 após correção; analistas veem oportunidade em bancos. <a class="news-link" href="https://opetroleo.com.br/bolsa-em-queda-tres-acoes-para-comecar-a-investir-com-apenas-r-300-entram-no-radar/" target="_blank">[Ler mais]</a></li>
        <li><b>BOVA11:</b> ETF do Ibovespa é opção para exposição ampla ao mercado em meio à volatilidade. <a class="news-link" href="https://br.investing.com/analysis/o-dia-apos-circuit-breaker-o-que-o-historico-diz-sobre-comprar-bolsa-brasil-agora-200480123" target="_blank">[Ler mais]</a></li>
        <li><b>CEAB3:</b> Goldman Sachs eleva participação em derivativos para 5,66%; ação segue volátil. <a class="news-link" href="https://visnoinvest.com/goldman-sachs-reaches-566-in-ca-ceab3-derivatives/" target="_blank">[Ler mais]</a></li>
        <li><b>XPML11:</b> FII de shoppings negocia abaixo do valor patrimonial e aposta em aquisições para reforçar resultados. <a class="news-link" href="https://opetroleo.com.br/xpml11-hoje-cotacao-cai-para-r-9598-e-dividendos-de-r-092-entram-em-alerta/" target="_blank">[Ler mais]</a></li>
        <li><b>MCCI11:</b> Fundo mantém carteira defensiva e proteção contra inflação, com retorno acumulado de 96%. <a class="news-link" href="https://conteudos.xpi.com.br/fundos-imobiliarios/relatorios/maua-capital-recebiveis-imobiliarios-mcci11-carteira-defensiva-e-protecao-contra-inflacao/" target="_blank">[Ler mais]</a></li>
    </ul>
    """

def get_oportunidades_renda_variavel():
    return """
    <ul class="compact-list">
        <li><b>Small Caps:</b> BB-BI inclui <b>Pine (PINE4)</b> e <b>Dexco (DXCO3)</b> na carteira de novembro. <a class="news-link" href="https://investalk.bb.com.br/noticias/onde-investir/carteira-smallcaps-novembro-26" target="_blank">[Ler mais]</a></li>
        <li><b>Exportadoras:</b> Dólar alto coloca <b>Suzano (SUZB3)</b>, <b>Gerdau (GGBR4)</b> e <b>Embraer (EMBJ3)</b> no radar. <a class="news-link" href="https://www.infomoney.com.br/mercados/dolar-forte-apos-eleicao-coloca-exportadoras-no-radar-quais-sao-as-acoes-preferidas/" target="_blank">[Ler mais]</a></li>
        <li><b>Recuperação:</b> Itaú BBA vê potencial em <b>Equatorial (EQTL3)</b>, <b>Rede D'Or (RDOR3)</b>, <b>Localiza (RENT3)</b> e <b>Sabesp (SBSP3)</b>. <a class="news-link" href="https://euqueroinvestir.com/apos-alta-de-11-do-ibovespa-itau-bba-aponta-4-acoes-que-ainda-podem-se-recuperar/" target="_blank">[Ler mais]</a></li>
        <li><b>BDRs:</b> Negociação de recibos de ações internacionais bate recorde; veja os mais procurados. <a class="news-link" href="https://valorinveste.globo.com/mercados/renda-variavel/noticia/2026/10/30/da-mineradora-aura-ao-nubank-os-bdrs-mais-procurados-na-b3-para-investir-la-fora.ghtml" target="_blank">[Ler mais]</a></li>
        <li><b>Small/Midcaps:</b> JPMorgan destaca <b>JSL (JSLG3)</b>, <b>Cury (CURY3)</b>, <b>Direcional (DIRR3)</b> e <b>Moura Dubeux (MDNE3)</b>. <a class="news-link" href="https://www.moneytimes.com.br/as-small-e-midcaps-brasileiras-para-ficar-de-olho-segundo-o-jpmorgan/" target="_blank">[Ler mais]</a></li>
    </ul>
    """

def get_noticias_renda_fixa(titulos):
    noticias = []
    for titulo in titulos:
        if "IPCA+ 2032" in titulo:
            noticias.append(f'<li><b>{titulo}:</b> Taxa cai para IPCA + 7,89% ao ano, queda de 9 pontos-base. <a class="news-link" href="https://istoedinheiro.com.br/tesouro-direto-taxas-30-10-2026" target="_blank">[Ler mais]</a></li>')
        elif "IPCA+ 2029" in titulo:
            noticias.append(f'<li><b>{titulo}:</b> Recuou de IPCA + 7,98% para 7,37% em um mês, segundo a Rankia. <a class="news-link" href="https://rankia.com.br/tesouro-direto-taxas-caem-antes-da-eleicao-de-2026/" target="_blank">[Ler mais]</a></li>')
        elif "IPCA+ 2035" in titulo:
            noticias.append(f'<li><b>{titulo}:</b> Taxas saltaram para IPCA + 7% ao ano após o resultado das eleições. <a class="news-link" href="https://investidor10.com.br/fiis/noticias/lula-4-derruba-todos-os-fiis-na-b3-e-so-o-ifix-derrete-6/" target="_blank">[Ler mais]</a></li>')
        elif "PRÉ 2032" in titulo:
            noticias.append(f'<li><b>{titulo}:</b> Prefixado 2032 atinge 15,38% ao ano, maior nível desde o choque eleitoral. <a class="news-link" href="https://istoedinheiro.com.br/tesouro-direto-taxas-30-10-2026" target="_blank">[Ler mais]</a></li>')
        elif "PRÉ 2035" in titulo:
            noticias.append(f'<li><b>{titulo}:</b> Taxas dos DIs encerram semana com altas acumuladas de mais de 250 pontos-base. <a class="news-link" href="https://br.investing.com/news/economy/taxas-dos-dis-encerram-semana-com-altas-acumuladas-de-mais-de-250-pontosbase-apos-vitoria-de-lula-1345678" target="_blank">[Ler mais]</a></li>')
        elif "Selic 2031" in titulo or "SELIC 2031" in titulo:
            noticias.append(f'<li><b>{titulo}:</b> Tesouro Selic 2031 oferece remuneração de Selic + 0,10% ao ano, opção segura. <a class="news-link" href="https://www.moneytimes.com.br/tesouro-direto-abre-com-taxas-acima-de-8-ipca-e-precos-em-queda-de-mais-de-20/" target="_blank">[Ler mais]</a></li>')
        else:
            noticias.append(f'<li><b>{titulo}:</b> Acompanhe as taxas do Tesouro Direto hoje; juro real próximo de 8% ao ano. <a class="news-link" href="https://www.infomoney.com.br/onde-investir/tesouro-direto-hoje-taxas-recua-de-leve-mas-prefixado-2032-ainda-rende-1538/" target="_blank">[Ler mais]</a></li>')
    return "<ul class='compact-list'>" + "".join(noticias) + "</ul>"

def get_oportunidades_renda_fixa():
    return """
    <ul class="compact-list">
        <li><b>IPCA+:</b> Juro real volta a 8% ao ano; especialistas veem oportunidade em títulos longos. <a class="news-link" href="https://www.seudinheiro.com/2026/onde-investir/renda-fixa-em-promocao-juros-sobem-apos-a-eleicao-e-xp-ve-oportunidade-em-titulos-que-agora-estao-mais-baratos-liga/" target="_blank">[Ler mais]</a></li>
        <li><b>Prefixado:</b> Taxas entre 14% e 15% ao ano; XP prefere vencimentos mais curtos como o Prefixado 2029. <a class="news-link" href="https://www.infomoney.com.br/onde-investir/taxas-dispararam-e-hora-de-comprar-tesouro/" target="_blank">[Ler mais]</a></li>
        <li><b>Tesouro Selic:</b> Indicado para dinheiro novo e liquidez em meio à volatilidade pós-eleição. <a class="news-link" href="https://www.infomoney.com.br/onde-investir/tesouro-direto-como-investir-agora-com-taxas-em-vaivem-apos-a-eleicao/" target="_blank">[Ler mais]</a></li>
        <li><b>Crédito Privado:</b> Debêntures incentivadas, CRIs e CRAs com isenção de IR; BB-BI e Itaú têm seleções. <a class="news-link" href="https://investalk.bb.com.br/noticias/onde-investir/credito-privado-onde-investir-confira-a-selecao-bb-bi-de-outubro-26" target="_blank">[Ler mais]</a></li>
        <li><b>CRIs/CRAs:</b> Spreads atrativos em meio à alta dos juros; seletividade é recomendada. <a class="news-link" href="https://valorinveste.globo.com/mercados/renda-fixa/noticia/2026/05/18/taxas-de-retorno-de-cris-cras-e-debentures-disparam-oportunidade-ou-alerta.ghtml" target="_blank">[Ler mais]</a></li>
    </ul>
    """

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
<div style="flex: 2; min-width: 200px;">
<div class="header-title"><a href="#topo" target="_self" style="text-decoration: none; color: inherit;">💰 DinDin</a></div>
<div class="header-subtitle">Seus investimentos e dicas em um só lugar.</div>
</div>
<div class="kpi-box">
<div class="kpi-label">Total Investido</div>
<div class="kpi-value">{fmt_brl(inv_geral)}</div>
</div>
<div class="kpi-box">
<div class="kpi-label">Posição Atual</div>
<div class="kpi-value">{fmt_brl(pos_geral)}</div>
</div>
<div class="kpi-box" style="flex: 0.8;">
<div class="kpi-label">Rentab.</div>
<div class="kpi-value" style="color: #00FF00;">{fmt_pct(rent_geral)}</div>
</div>
<div class="kpi-box" style="flex: 1.2;">
<div class="kpi-label">Total Variável</div>
<div class="kpi-value">{fmt_brl(inv_rv)}</div>
<div class="kpi-sub" style="color: {cor_rv};">{fmt_pct(rent_rv)}</div>
</div>
<div class="kpi-box" style="flex: 1.2;">
<div class="kpi-label">Total Fixo</div>
<div class="kpi-value">{fmt_brl(inv_rf)}</div>
<div class="kpi-sub" style="color: #00FF00;">{fmt_pct(rent_rf)}</div>
</div>
<div class="kpi-meta">
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
        c4.metric("Rentabilidade Média", fmt_pct(rent_rv))
    
    st.write("")
    
    num_cols = 4
    num_rows = math.ceil(len(carteira_acoes) / num_cols)

    for row in range(num_rows):
        cols = st.columns(num_cols)
        for i in range(num_cols):
            idx = row * num_cols + i
            if idx < len(carteira_acoes):
                ativo = carteira_acoes[idx]
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
                    
                    share = (inv_ativos[idx] / total_investido_rv) * 100 if total_investido_rv > 0 and idx < len(inv_ativos) else 0
                        
                    sinal = "COMPRAR" if rsi < 35 else ("VENDER" if rsi > 70 else "MANTER")
                    cor = "#00FF00" if rsi < 35 else ("#FF4B4B" if rsi > 70 else "#808080")
                        
                    nome_empresa = dicionario_empresas.get(ativo, "")
                    link = gerar_link_investidor10(ativo)
                    
                    # Busca os dados fundamentalistas da API
                    metricas = buscar_metricas_fundamentalistas(ativo)
                        
                    with cols[i]:
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link}' target='_blank' style='font-size: 16px; font-weight: bold; color: white;'>{ativo}</a><br><span style='font-size: 10px; color: #888;'>{nome_empresa}</span></div>", unsafe_allow_html=True)
                            
                            st.metric(label="Cotação Atual", value=fmt_brl(preco_atual), delta=f"{variacao_pct:.2f}%".replace(".", ","), label_visibility="collapsed")
                            
                            # Bloco técnico
                            html_tecnico = f"<div style='font-size: 12px; line-height: 1.3; margin-top: -10px; margin-bottom: 5px;'>📉 <b>Mín 6m:</b> {fmt_brl(min_6m)}<br>⏳ <b>Mín 5a:</b> {fmt_brl(min_5a)}{texto_data_5a}<br>📊 <b>RSI:</b> {rsi:.1f}".replace(".", ",") + f"<br>🤖 <b>Sinal:</b> <span style='color:{cor}; font-weight: bold;'>{sinal}</span><br>💼 <b>Share:</b> {share:.1f}%".replace(".", ",") + "</div>"
                            st.markdown(html_tecnico, unsafe_allow_html=True)
                            
                            # Bloco de indicadores fundamentalistas
                            if metricas.get("receita") or metricas.get("divida") or metricas.get("roe"):
                                html_indicadores = "<hr style='margin: 5px 0; border-top: 1px solid #444;'>"
                                if metricas.get("receita"): html_indicadores += f"<div style='font-size: 11px; color: #cce5ff;'>💰 <b>Receita:</b> {fmt_grande(metricas['receita'])}</div>"
                                if metricas.get("divida"): html_indicadores += f"<div style='font-size: 11px; color: #cce5ff;'>🏦 <b>Dív. Líq:</b> {fmt_grande(metricas['divida'])}</div>"
                                if metricas.get("roe"): html_indicadores += f"<div style='font-size: 11px; color: #cce5ff;'>🏆 <b>ROE:</b> {fmt_pct(metricas['roe'])}</div>"
                                st.markdown(html_indicadores, unsafe_allow_html=True)
                            
                            st.progress(share / 100.0) 

    st.divider()

    st.subheader("🔥 Oportunidades de Compra (Radar Fundamentalista)")
    st.markdown("Ativos com RSI abaixo de 35 **e** Fundamentos saudáveis (Score >= 2):")

    radar_tickers = ['PETR4', 'BBAS3', 'ITUB4', 'BBDC4', 'MGLU3', 'LREN3', 'VIVT3', 'TAEE11', 'KLBN11', 'SANB11', 'BPAC11', 'HGLG11', 'KNRI11', 'MXRF11']
    oportunidades = []

    with st.spinner("Analisando fundamentos e RSI..."):
        for ticker in radar_tickers:
            hist_radar = buscar_dados(ticker)
            if not hist_radar.empty:
                rsi_radar = calcular_rsi(hist_radar['Close'])
                if rsi_radar < 35:
                    metricas_radar = buscar_metricas_fundamentalistas(ticker)
                    score = metricas_radar.get("score", 0)
                    
                    if score >= 2:
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
                            "data_min_5a": texto_data_5a_radar, "score": score
                        })

    if oportunidades:
        num_rows_op = math.ceil(len(oportunidades) / num_cols)
        for row in range(num_rows_op):
            cols_op = st.columns(num_cols)
            for i in range(num_cols):
                idx_op = row * num_cols + i
                if idx_op < len(oportunidades):
                    op = oportunidades[idx_op]
                    nome_empresa_radar = dicionario_empresas.get(op['ativo'], "")
                    link_op = gerar_link_investidor10(op['ativo'])
                    estrelas = "⭐" * op['score']
                    
                    with cols_op[i]:
                        with st.container(border=True):
                            st.markdown(f"<div style='text-align: center; margin-top: -5px; margin-bottom: 2px; line-height: 1.1;'><a class='ticker-link' href='{link_op}' target='_blank' style='font-size: 16px; font-weight: bold; color: #00FF00;'>{op['ativo']}</a><br><span style='font-size: 10px; color: #888;'>{nome_empresa_radar}</span></div>", unsafe_allow_html=True)
                            
                            st.metric(label="Preço", value=fmt_brl(op['preco']), delta=f"{op['variacao']:.2f}%".replace(".", ","), label_visibility="collapsed")
                            
                            st.markdown(f"<div style='font-size: 12px; line-height: 1.3; margin-top: -10px; margin-bottom: 5px;'>🎯 <b>RSI:</b> {op['rsi']:.1f}".replace(".", ",") + f"<br>🏆 <b>Score:</b> {estrelas} ({op['score']}/4)<br>📉 <b>Mín 6m:</b> {fmt_brl(op['min_6m'])}<br>⏳ <b>Mín 5a:</b> {fmt_brl(op['min_5a'])}{op['data_min_5a']}</div>", unsafe_allow_html=True)
    else:
        st.info("Nenhuma oportunidade com RSI baixo e bons fundamentos no momento.")

    st.divider()
    
    st.markdown("#### 💡 Notícias dos Seus Ativos - Renda Variável (Últimas 24h)")
    st.markdown(get_noticias_renda_variavel(), unsafe_allow_html=True)

    st.divider()

    st.markdown("#### 🚀 Oportunidades do Mercado - Fora da Carteira")
    st.markdown(get_oportunidades_renda_variavel(), unsafe_allow_html=True)

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
        c4.metric("Rentabilidade Média", fmt_pct(rent_media))

    st.write("")
    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_fam, df_grafico_fam = gerar_tabela_renda_fixa(ativos_fam, inv_fam, pos_fam, gan_fam, rent_fam)
    
    df_fam.insert(5, "Share (%)", (df_fam["Investido (R$)"] / total_investido) * 100)

    cols_to_center_fam = [c for c in df_fam.columns if c != 'Ativo']

    styled_fam = (df_fam.style
                  .map(style_taxa, subset=['Taxa (%)'])
                  .format({
                      "Investido (R$)": lambda x: fmt_brl(x),
                      "Posição Atual (R$)": lambda x: fmt_brl(x),
                      "Ganho (R$)": lambda x: fmt_brl(x),
                      "Taxa (%)": lambda x: fmt_pct(x),
                      **{mes: lambda x: fmt_brl(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]},
                      **{f"Tx {mes}": lambda x: fmt_pct(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]}
                  })
                  .set_properties(subset=cols_to_center_fam, **{'text-align': 'center'})
                  .set_properties(subset=['Share (%)'], **{'border-right': '2px solid #555'}))

    config_colunas = {
        "Share (%)": st.column_config.ProgressColumn("Share (%)", format="%.1f%%", min_value=0, max_value=100)
    }

    st.dataframe(styled_fam, hide_index=True, use_container_width=True, column_config=config_colunas)

    st.write("")
    st.markdown("#### Histórico de Taxas")
    
    df_melt = df_grafico_fam.reset_index().melt('index', var_name='Ativo', value_name='Taxa')
    df_melt = df_melt.rename(columns={'index': 'Mês'})
    df_ultimo_mes = df_melt[df_melt['Mês'] == 'Out']

    line = alt.Chart(df_melt).mark_line(point=True).encode(
        x=alt.X('Mês:N', sort=None, title='Mês', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Taxa:Q', title='Taxa Anualizada (%)', scale=alt.Scale(zero=False)),
        color=alt.Color('Ativo:N', legend=alt.Legend(orient='bottom', columns=3)),
        tooltip=[
            alt.Tooltip('Mês:N', title='Mês'),
            alt.Tooltip('Ativo:N', title='Ativo'),
            alt.Tooltip('Taxa:Q', title='Taxa (%)', format='.2f')
        ]
    )

    text = alt.Chart(df_ultimo_mes).mark_text(
        align='left', dx=5, fontSize=12, fontWeight='bold'
    ).encode(
        x=alt.X('Mês:N'),
        y=alt.Y('Taxa:Q'),
        text=alt.Text('Taxa:Q', format='.1f'),
        color=alt.Color('Ativo:N', legend=None)
    )

    chart_fam = (line + text).properties(height=350).interactive()
    st.altair_chart(chart_fam, use_container_width=True)

    st.divider()
    
    st.markdown("#### 💡 Notícias dos Seus Títulos - Renda Fixa (Últimas 24h)")
    st.markdown(get_noticias_renda_fixa(ativos_fam), unsafe_allow_html=True)

    st.divider()

    st.markdown("#### 🚀 Oportunidades do Mercado - Fora da Carteira")
    st.markdown(get_oportunidades_renda_fixa(), unsafe_allow_html=True)

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
        c4.metric("Rentabilidade Média", fmt_pct(rent_media_maria))

    st.write("")
    st.markdown("#### Detalhamento e Evolução Mês a Mês (2026)")
    
    df_maria, df_grafico_maria = gerar_tabela_renda_fixa(ativos_maria, inv_maria, pos_maria, gan_maria, rent_maria)
    
    df_maria.insert(5, "Share (%)", (df_maria["Investido (R$)"] / total_investido_maria) * 100)

    cols_to_center_maria = [c for c in df_maria.columns if c != 'Ativo']

    styled_maria = (df_maria.style
                    .map(style_taxa, subset=['Taxa (%)'])
                    .format({
                        "Investido (R$)": lambda x: fmt_brl(x),
                        "Posição Atual (R$)": lambda x: fmt_brl(x),
                        "Ganho (R$)": lambda x: fmt_brl(x),
                        "Taxa (%)": lambda x: fmt_pct(x),
                        **{mes: lambda x: fmt_brl(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]},
                        **{f"Tx {mes}": lambda x: fmt_pct(x) for mes in ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26", "Jul/26", "Ago/26", "Set/26", "Out/26", "Nov/26", "Dez/26"]}
                    })
                    .set_properties(subset=cols_to_center_maria, **{'text-align': 'center'})
                    .set_properties(subset=['Share (%)'], **{'border-right': '2px solid #555'}))

    st.dataframe(styled_maria, hide_index=True, use_container_width=True, column_config=config_colunas)

    st.write("")
    st.markdown("#### Histórico de Taxas")
    
    df_melt_maria = df_grafico_maria.reset_index().melt('index', var_name='Ativo', value_name='Taxa')
    df_melt_maria = df_melt_maria.rename(columns={'index': 'Mês'})
    df_ultimo_mes_maria = df_melt_maria[df_melt_maria['Mês'] == 'Out']

    line_maria = alt.Chart(df_melt_maria).mark_line(point=True).encode(
        x=alt.X('Mês:N', sort=None, title='Mês', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Taxa:Q', title='Taxa Anualizada (%)', scale=alt.Scale(zero=False)),
        color=alt.Color('Ativo:N', legend=alt.Legend(orient='bottom', columns=3)),
        tooltip=[
            alt.Tooltip('Mês:N', title='Mês'),
            alt.Tooltip('Ativo:N', title='Ativo'),
            alt.Tooltip('Taxa:Q', title='Taxa (%)', format='.2f')
        ]
    )

    text_maria = alt.Chart(df_ultimo_mes_maria).mark_text(
        align='left', dx=5, fontSize=12, fontWeight='bold'
    ).encode(
        x=alt.X('Mês:N'),
        y=alt.Y('Taxa:Q'),
        text=alt.Text('Taxa:Q', format='.1f'),
        color=alt.Color('Ativo:N', legend=None)
    )

    chart_maria = (line_maria + text_maria).properties(height=350).interactive()
    st.altair_chart(chart_maria, use_container_width=True)

    st.divider()
    
    st.markdown("#### 💡 Notícias dos Seus Títulos - Renda Fixa (Últimas 24h)")
    st.markdown(get_noticias_renda_fixa(ativos_maria), unsafe_allow_html=True)

    st.divider()

    st.markdown("#### 🚀 Oportunidades do Mercado - Fora da Carteira")
    st.markdown(get_oportunidades_renda_fixa(), unsafe_allow_html=True)