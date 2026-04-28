"""
Market Breadth ELITE Setorial - Ibovespa

Recursos:
- Busca automática da carteira teórica do Ibovespa na B3;
- Fallback manual editável;
- Download de preços pelo Yahoo Finance;
- Breadth por MM20, MM50 e MM200:
    - percentual simples;
    - percentual ponderado pelo peso da carteira, quando a B3 fornece participação;
- Advance/Decline Line aproximada;
- Divergência entre IBOV e breadth;
- Regime de mercado:
    - Risk-on;
    - Neutro;
    - Atenção;
    - Risk-off;
- Ranking por ativo;
- Exportação CSV.

Instalação:
pip install -r requirements.txt

Execução:
streamlit run breadth_ibov_elite.py
"""

import base64
import json

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import altair as alt


FALLBACK_TICKERS = [
    "ABEV3.SA", "ALOS3.SA", "ASAI3.SA", "AZZA3.SA", "B3SA3.SA",
    "BBAS3.SA", "BBDC3.SA", "BBDC4.SA", "BBSE3.SA", "BEEF3.SA",
    "BPAC11.SA", "BRAP4.SA", "BRAV3.SA", "BRFS3.SA", "CMIG4.SA",
    "CMIN3.SA", "COGN3.SA", "CPFE3.SA", "CPLE6.SA", "CSAN3.SA",
    "CSMG3.SA", "CSNA3.SA", "CYRE3.SA", "DIRR3.SA", "EGIE3.SA",
    "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENEV3.SA", "ENGI11.SA",
    "EQTL3.SA", "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", "HAPV3.SA",
    "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", "ITSA4.SA", "ITUB4.SA",
    "KLBN11.SA", "LREN3.SA", "MGLU3.SA", "MRFG3.SA", "MULT3.SA",
    "NTCO3.SA", "PCAR3.SA", "PETR3.SA", "PETR4.SA", "PETZ3.SA",
    "PRIO3.SA", "PSSA3.SA", "RADL3.SA", "RAIL3.SA", "RAIZ4.SA",
    "RDOR3.SA", "RECV3.SA", "RENT3.SA", "SANB11.SA", "SBSP3.SA",
    "SLCE3.SA", "SMFT3.SA", "SMTO3.SA", "SUZB3.SA", "TAEE11.SA",
    "TIMS3.SA", "TOTS3.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA",
    "VAMO3.SA", "VBBR3.SA", "VIVA3.SA", "VIVT3.SA", "WEGE3.SA",
    "YDUQ3.SA"
]


# Mapeamento setorial aproximado dos principais ativos do Ibovespa.
# Pode ser ajustado livremente conforme sua metodologia.
SETOR_POR_CODIGO = {
    # Bancos e serviços financeiros
    "BBAS3": "Financeiro",
    "BBDC3": "Financeiro",
    "BBDC4": "Financeiro",
    "ITUB4": "Financeiro",
    "ITSA4": "Financeiro",
    "BPAC11": "Financeiro",
    "SANB11": "Financeiro",
    "BBSE3": "Seguros",
    "PSSA3": "Seguros",
    "B3SA3": "Serviços Financeiros",

    # Petróleo, gás e combustíveis
    "PETR3": "Petróleo, Gás e Combustíveis",
    "PETR4": "Petróleo, Gás e Combustíveis",
    "PRIO3": "Petróleo, Gás e Combustíveis",
    "RECV3": "Petróleo, Gás e Combustíveis",
    "BRAV3": "Petróleo, Gás e Combustíveis",
    "RAIZ4": "Petróleo, Gás e Combustíveis",
    "UGPA3": "Petróleo, Gás e Combustíveis",
    "VBBR3": "Petróleo, Gás e Combustíveis",
    "CSAN3": "Petróleo, Gás e Combustíveis",

    # Mineração, siderurgia e papel/celulose
    "VALE3": "Mineração e Siderurgia",
    "CMIN3": "Mineração e Siderurgia",
    "CSNA3": "Mineração e Siderurgia",
    "GGBR4": "Mineração e Siderurgia",
    "GOAU4": "Mineração e Siderurgia",
    "USIM5": "Mineração e Siderurgia",
    "BRAP4": "Mineração e Siderurgia",
    "SUZB3": "Papel e Celulose",
    "KLBN11": "Papel e Celulose",

    # Energia elétrica e saneamento
    "ELET3": "Energia Elétrica",
    "ELET6": "Energia Elétrica",
    "EQTL3": "Energia Elétrica",
    "CMIG4": "Energia Elétrica",
    "CPLE6": "Energia Elétrica",
    "CPFE3": "Energia Elétrica",
    "EGIE3": "Energia Elétrica",
    "TAEE11": "Energia Elétrica",
    "ENEV3": "Energia Elétrica",
    "SBSP3": "Saneamento",
    "CSMG3": "Saneamento",

    # Consumo, varejo e alimentos
    "ABEV3": "Consumo",
    "ASAI3": "Varejo e Consumo",
    "CRFB3": "Varejo e Consumo",
    "PCAR3": "Varejo e Consumo",
    "LREN3": "Varejo e Consumo",
    "MGLU3": "Varejo e Consumo",
    "PETZ3": "Varejo e Consumo",
    "AZZA3": "Varejo e Consumo",
    "VIVA3": "Varejo e Consumo",
    "NTCO3": "Varejo e Consumo",
    "BRFS3": "Alimentos",
    "JBSS3": "Alimentos",
    "MRFG3": "Alimentos",
    "BEEF3": "Alimentos",
    "SMTO3": "Alimentos",
    "SLCE3": "Agro",

    # Saúde e educação
    "RADL3": "Saúde",
    "HAPV3": "Saúde",
    "RDOR3": "Saúde",
    "FLRY3": "Saúde",
    "HYPE3": "Saúde",
    "COGN3": "Educação",
    "YDUQ3": "Educação",

    # Construção, imóveis e shoppings
    "CYRE3": "Construção e Imóveis",
    "MRVE3": "Construção e Imóveis",
    "EZTC3": "Construção e Imóveis",
    "DIRR3": "Construção e Imóveis",
    "MULT3": "Shoppings e Propriedades",
    "ALOS3": "Shoppings e Propriedades",
    "IGTI11": "Shoppings e Propriedades",

    # Transporte, locação e infraestrutura
    "RAIL3": "Transporte e Infraestrutura",
    "CCRO3": "Transporte e Infraestrutura",
    "AZUL4": "Transporte e Infraestrutura",
    "RENT3": "Locação e Mobilidade",
    "VAMO3": "Locação e Mobilidade",

    # Tecnologia, telecom e indústria
    "WEGE3": "Indústria",
    "EMBR3": "Indústria",
    "TOTS3": "Tecnologia",
    "TIMS3": "Telecom",
    "VIVT3": "Telecom",

    # Química e petroquímica
    "BRKM5": "Química e Petroquímica",
}


def montar_url_b3(indice="IBOV", page_number=1, page_size=200, language="pt-br"):
    payload = {
        "language": language,
        "pageNumber": page_number,
        "pageSize": page_size,
        "index": indice,
        "segment": "1"
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("utf-8")

    return f"https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/{payload_b64}"


def parse_percentual_b3(valor):
    if valor is None:
        return None

    texto = str(valor).strip()

    if not texto:
        return None

    texto = texto.replace(".", "").replace(",", ".")

    try:
        return float(texto)
    except ValueError:
        return None


def normalizar_ticker_yahoo(ticker):
    ticker = str(ticker).strip().upper().replace(" ", "")

    if not ticker:
        return None

    if ticker.endswith(".SA"):
        return ticker

    return f"{ticker}.SA"


def criar_carteira_manual(texto):
    texto = texto.replace(";", ",").replace("\n", ",")
    tickers = []

    for parte in texto.split(","):
        ticker = normalizar_ticker_yahoo(parte)

        if ticker:
            tickers.append(ticker)

    tickers = sorted(list(set(tickers)))

    return pd.DataFrame({
        "codigo": [t.replace(".SA", "") for t in tickers],
        "ticker_yahoo": tickers,
        "acao": None,
        "tipo": None,
        "quantidade_teorica": None,
        "participacao_pct": None,
    })


@st.cache_data(ttl=60 * 60)
def buscar_carteira_ibov_b3():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Origin": "https://sistemaswebb3-listados.b3.com.br",
        "Referer": "https://sistemaswebb3-listados.b3.com.br/"
    }

    urls = [
        montar_url_b3(language="pt-br"),
        montar_url_b3(language="en-us"),
        "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/IBOV?language=pt-br&pageNumber=1&pageSize=200",
    ]

    ultimo_erro = None

    for url in urls:
        try:
            resposta = requests.get(url, headers=headers, timeout=30)
            resposta.raise_for_status()

            if not resposta.text.strip().startswith("{"):
                raise RuntimeError("A B3 não retornou JSON.")

            dados = resposta.json()
            resultados = dados.get("results", [])

            if not resultados:
                raise RuntimeError("A B3 retornou JSON sem lista de ativos.")

            linhas = []

            for item in resultados:
                codigo = item.get("cod") or item.get("codigo") or item.get("code") or item.get("symbol")

                if not codigo:
                    continue

                codigo = str(codigo).strip().upper()

                if codigo in ["IBOV", "TOTAL", "QUANTIDADE TEÓRICA TOTAL"]:
                    continue

                if len(codigo) < 5:
                    continue

                linhas.append({
                    "codigo": codigo,
                    "ticker_yahoo": f"{codigo}.SA",
                    "acao": item.get("asset") or item.get("acao") or item.get("companyName"),
                    "tipo": item.get("type") or item.get("tipo"),
                    "quantidade_teorica": item.get("theoricalQty") or item.get("qtdeTeorica"),
                    "participacao_pct": parse_percentual_b3(item.get("part") or item.get("partAcum")),
                })

            df = pd.DataFrame(linhas)

            if not df.empty:
                return df.drop_duplicates(subset=["codigo"]).sort_values("codigo").reset_index(drop=True)

        except Exception as erro:
            ultimo_erro = erro

    raise RuntimeError(f"Não foi possível buscar carteira na B3. Último erro: {ultimo_erro}")


@st.cache_data(ttl=30 * 60)
def baixar_precos_yahoo(tickers, periodo="2y"):
    dados = yf.download(
        tickers=tickers,
        period=periodo,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False
    )

    fechamentos = pd.DataFrame()

    if len(tickers) == 1:
        ticker = tickers[0]
        if "Close" in dados.columns:
            fechamentos[ticker] = dados["Close"]
    else:
        for ticker in tickers:
            try:
                fechamentos[ticker] = dados[ticker]["Close"]
            except Exception:
                continue

    return fechamentos.dropna(how="all")


@st.cache_data(ttl=30 * 60)
def baixar_ibov(periodo="2y"):
    dados = yf.download(
        "^BVSP",
        period=periodo,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    if dados.empty:
        return pd.DataFrame()

    df = pd.DataFrame(index=dados.index)
    df["IBOV"] = dados["Close"]

    for media in [20, 50, 200]:
        df[f"MM{media}"] = df["IBOV"].rolling(media).mean()

    return df


def calcular_breadth(fechamentos, carteira, medias=(20, 50, 200)):
    resultado = pd.DataFrame(index=fechamentos.index)
    resultado["Total ativos válidos"] = fechamentos.notna().sum(axis=1)

    pesos = (
        carteira.set_index("ticker_yahoo")["participacao_pct"]
        .reindex(fechamentos.columns)
        .astype("float64")
    )

    tem_pesos = pesos.notna().sum() > 0 and pesos.sum(skipna=True) > 0

    for media in medias:
        mm = fechamentos.rolling(media).mean()
        base_valida = fechamentos.notna() & mm.notna()
        acima = (fechamentos > mm) & base_valida

        qtd_acima = acima.sum(axis=1)
        qtd_validos = base_valida.sum(axis=1)

        qtd_validos_seguro = qtd_validos.replace(0, pd.NA)

        resultado[f"Qtd acima MM{media}"] = qtd_acima
        resultado[f"Base válida MM{media}"] = qtd_validos
        resultado[f"% acima MM{media}"] = qtd_acima / qtd_validos_seguro * 100

        if tem_pesos:
            pesos_validos = base_valida.multiply(pesos, axis=1).sum(axis=1)
            pesos_acima = acima.multiply(pesos, axis=1).sum(axis=1)
            pesos_validos_seguro = pesos_validos.replace(0, pd.NA)
            resultado[f"% ponderado acima MM{media}"] = pesos_acima / pesos_validos_seguro * 100

    return resultado


def calcular_advance_decline(fechamentos):
    retornos = fechamentos.pct_change()
    advances = (retornos > 0).sum(axis=1)
    declines = (retornos < 0).sum(axis=1)

    ad = pd.DataFrame(index=fechamentos.index)
    ad["Advances"] = advances
    ad["Declines"] = declines
    ad["Net Advances"] = advances - declines
    ad["Advance/Decline Line"] = ad["Net Advances"].cumsum()

    return ad


def calcular_tabela_ativos(fechamentos, carteira):
    linhas = []

    for ticker in fechamentos.columns:
        serie = fechamentos[ticker].dropna()

        if serie.empty:
            continue

        fechamento = serie.iloc[-1]

        linha = {
            "codigo": ticker.replace(".SA", ""),
            "ticker_yahoo": ticker,
            "ultimo_fechamento": fechamento,
            "retorno_5d_pct": (serie.iloc[-1] / serie.iloc[-6] - 1) * 100 if len(serie) >= 6 else None,
            "retorno_21d_pct": (serie.iloc[-1] / serie.iloc[-22] - 1) * 100 if len(serie) >= 22 else None,
        }

        for media in [20, 50, 200]:
            mm = serie.rolling(media).mean().iloc[-1]

            linha[f"MM{media}"] = mm
            linha[f"acima_MM{media}"] = bool(fechamento > mm) if pd.notna(mm) else None
            linha[f"dist_MM{media}_pct"] = ((fechamento / mm) - 1) * 100 if pd.notna(mm) and mm != 0 else None

        linhas.append(linha)

    df = pd.DataFrame(linhas)

    if df.empty:
        return df

    df = df.merge(
        carteira[["codigo", "acao", "tipo", "participacao_pct"]],
        on="codigo",
        how="left"
    )

    return df.sort_values("dist_MM20_pct", ascending=False)


def detectar_divergencia(ibov, breadth, janela=21):
    if ibov.empty or breadth.empty:
        return "Sem dados suficientes para avaliar divergência."

    base = pd.concat(
        [
            ibov["IBOV"].rename("IBOV"),
            breadth["% acima MM20"].rename("Breadth_MM20"),
            breadth["% acima MM50"].rename("Breadth_MM50"),
        ],
        axis=1
    ).dropna()

    if len(base) < janela + 1:
        return "Sem histórico suficiente para avaliar divergência."

    ibov_var = base["IBOV"].iloc[-1] / base["IBOV"].iloc[-janela] - 1
    b20_var = base["Breadth_MM20"].iloc[-1] - base["Breadth_MM20"].iloc[-janela]
    b50_var = base["Breadth_MM50"].iloc[-1] - base["Breadth_MM50"].iloc[-janela]

    if ibov_var > 0 and b20_var < -10 and b50_var < -5:
        return "Divergência baixista: IBOV subiu, mas a participação interna caiu."

    if ibov_var < 0 and b20_var > 10 and b50_var > 5:
        return "Divergência altista: IBOV caiu, mas a participação interna melhorou."

    return "Sem divergência relevante no momento."


def classificar_regime(ultima):
    b20 = ultima.get("% acima MM20")
    b50 = ultima.get("% acima MM50")
    b200 = ultima.get("% acima MM200")

    if pd.isna(b20) or pd.isna(b50) or pd.isna(b200):
        return "Neutro", "Ainda há dados insuficientes para classificar o regime completo."

    if b20 >= 60 and b50 >= 55 and b200 >= 50:
        return "Risk-on", "Mercado com boa participação interna e sustentação estrutural."

    if b20 < 35 and b50 < 40 and b200 < 45:
        return "Risk-off", "Mercado com baixa participação interna e fraqueza estrutural."

    if b20 < 40 and b50 >= 50:
        return "Atenção", "Curto prazo enfraquecendo, mas estrutura intermediária ainda resiste."

    if b20 >= 60 and b50 < 45:
        return "Repique técnico", "Curto prazo melhorou, mas a base intermediária ainda é frágil."

    return "Neutro", "Mercado sem sinal extremo de amplitude."


def formatar_pct(valor):
    if pd.isna(valor):
        return "N/D"
    return f"{valor:.1f}%"



def preparar_dataframe_plot(df, colunas):
    """
    Prepara DataFrame em formato longo para gráficos Altair.
    Funciona mesmo quando o índice de datas vem com nomes diferentes.
    """
    dados = df[colunas].copy()
    dados = dados.reset_index()

    coluna_data = dados.columns[0]
    dados = dados.rename(columns={coluna_data: "Data"})

    dados_longos = dados.melt(
        id_vars="Data",
        var_name="Indicador",
        value_name="Valor"
    )

    return dados_longos


def grafico_medias_coloridas(df, colunas, titulo_eixo_y="Valor"):
    """
    Plota MM20 em verde, MM50 em amarelo e MM200 em vermelho.
    Usado para breadth simples, breadth ponderado, quantidade e IBOV com médias.
    """
    dados_longos = preparar_dataframe_plot(df, colunas)

    mapa_cores = {
        "% acima MM20": "#00A000",
        "% acima MM50": "#FFD700",
        "% acima MM200": "#D62728",

        "% ponderado acima MM20": "#00A000",
        "% ponderado acima MM50": "#FFD700",
        "% ponderado acima MM200": "#D62728",

        "Qtd acima MM20": "#00A000",
        "Qtd acima MM50": "#FFD700",
        "Qtd acima MM200": "#D62728",

        "MM20": "#00A000",
        "MM50": "#FFD700",
        "MM200": "#D62728",
        "IBOV": "#1F77B4",
    }

    domain = [c for c in colunas]
    range_cores = [mapa_cores.get(c, "#1F77B4") for c in colunas]

    zoom_x = alt.selection_interval(
        bind="scales",
        encodings=["x"],
        name="zoom_temporal_medias"
    )

    chart = (
        alt.Chart(dados_longos)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Data:T", title="Data"),
            y=alt.Y("Valor:Q", title=titulo_eixo_y),
            color=alt.Color(
                "Indicador:N",
                scale=alt.Scale(domain=domain, range=range_cores),
                legend=alt.Legend(title="Indicador")
            ),
            tooltip=[
                alt.Tooltip("Data:T", title="Data"),
                alt.Tooltip("Indicador:N", title="Indicador"),
                alt.Tooltip("Valor:Q", title="Valor", format=".2f"),
            ],
        )
        .properties(height=420)
        .add_params(zoom_x)
    )

    st.altair_chart(chart, use_container_width=True)


def grafico_linha_simples(df, colunas, titulo_eixo_y="Valor"):
    """
    Gráfico simples para indicadores que não usam MM20/MM50/MM200.
    """
    dados_longos = preparar_dataframe_plot(df, colunas)

    zoom_x = alt.selection_interval(
        bind="scales",
        encodings=["x"],
        name="zoom_temporal_linha"
    )

    chart = (
        alt.Chart(dados_longos)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Data:T", title="Data"),
            y=alt.Y("Valor:Q", title=titulo_eixo_y),
            color=alt.Color("Indicador:N", legend=alt.Legend(title="Indicador")),
            tooltip=[
                alt.Tooltip("Data:T", title="Data"),
                alt.Tooltip("Indicador:N", title="Indicador"),
                alt.Tooltip("Valor:Q", title="Valor", format=".2f"),
            ],
        )
        .properties(height=420)
        .add_params(zoom_x)
    )

    st.altair_chart(chart, use_container_width=True)


def aplicar_setores(carteira):
    """
    Adiciona coluna Setor usando o mapa SETOR_POR_CODIGO.
    Ativos não mapeados ficam como 'Não classificado'.
    """
    carteira = carteira.copy()
    carteira["setor"] = carteira["codigo"].map(SETOR_POR_CODIGO).fillna("Não classificado")
    return carteira


def calcular_breadth_por_setor(fechamentos, carteira, medias=(20, 50, 200)):
    """
    Calcula breadth por setor na data mais recente disponível.

    Retorna tabela com:
    - setor
    - quantidade de ativos
    - % acima MM20, MM50 e MM200
    - % ponderado acima MM20, MM50 e MM200, quando houver pesos da B3
    """
    if fechamentos.empty or carteira.empty:
        return pd.DataFrame()

    carteira_setores = aplicar_setores(carteira)
    ultima_data = fechamentos.dropna(how="all").index.max()

    linhas = []

    for setor, grupo in carteira_setores.groupby("setor"):
        tickers_setor = [
            ticker for ticker in grupo["ticker_yahoo"].dropna().tolist()
            if ticker in fechamentos.columns
        ]

        if not tickers_setor:
            continue

        precos_setor = fechamentos[tickers_setor]
        linha = {
            "setor": setor,
            "ativos_no_setor": len(tickers_setor),
        }

        pesos = (
            grupo.set_index("ticker_yahoo")["participacao_pct"]
            .reindex(tickers_setor)
            .astype("float64")
        )

        tem_pesos = pesos.notna().sum() > 0 and pesos.sum(skipna=True) > 0

        for media in medias:
            mm = precos_setor.rolling(media).mean()

            fechamento_ultimo = precos_setor.loc[ultima_data]
            mm_ultima = mm.loc[ultima_data]

            base_valida = fechamento_ultimo.notna() & mm_ultima.notna()
            acima = (fechamento_ultimo > mm_ultima) & base_valida

            qtd_validos = int(base_valida.sum())
            qtd_acima = int(acima.sum())

            linha[f"base_MM{media}"] = qtd_validos
            linha[f"qtd_acima_MM{media}"] = qtd_acima
            linha[f"% acima MM{media}"] = (qtd_acima / qtd_validos * 100) if qtd_validos > 0 else pd.NA

            if tem_pesos:
                pesos_validos = pesos[base_valida]
                pesos_acima = pesos[acima]
                soma_validos = pesos_validos.sum(skipna=True)

                linha[f"% ponderado acima MM{media}"] = (
                    pesos_acima.sum(skipna=True) / soma_validos * 100
                    if soma_validos > 0
                    else pd.NA
                )

        linhas.append(linha)

    df = pd.DataFrame(linhas)

    if df.empty:
        return df

    return df.sort_values("% acima MM20", ascending=False)


def calcular_historico_breadth_setorial(fechamentos, carteira, media=20):
    """
    Calcula o histórico do breadth por setor para uma média específica.
    Usado para comparar a evolução setorial no gráfico.
    """
    if fechamentos.empty or carteira.empty:
        return pd.DataFrame()

    carteira_setores = aplicar_setores(carteira)
    resultado = pd.DataFrame(index=fechamentos.index)

    for setor, grupo in carteira_setores.groupby("setor"):
        tickers_setor = [
            ticker for ticker in grupo["ticker_yahoo"].dropna().tolist()
            if ticker in fechamentos.columns
        ]

        if not tickers_setor:
            continue

        precos_setor = fechamentos[tickers_setor]
        mm = precos_setor.rolling(media).mean()

        base_valida = precos_setor.notna() & mm.notna()
        acima = (precos_setor > mm) & base_valida

        qtd_validos = base_valida.sum(axis=1).replace(0, pd.NA)
        qtd_acima = acima.sum(axis=1)

        resultado[setor] = qtd_acima / qtd_validos * 100

    return resultado


def grafico_setorial_linhas(df_setorial, titulo_eixo_y="% acima da média"):
    """
    Gráfico de linhas para comparação dos setores.
    """
    if df_setorial.empty:
        st.info("Sem dados setoriais suficientes para o gráfico.")
        return

    dados = df_setorial.reset_index()
    coluna_data = dados.columns[0]
    dados = dados.rename(columns={coluna_data: "Data"})

    dados_longos = dados.melt(
        id_vars="Data",
        var_name="Setor",
        value_name="Valor"
    ).dropna()

    zoom_x = alt.selection_interval(
        bind="scales",
        encodings=["x"],
        name="zoom_temporal_setorial"
    )

    chart = (
        alt.Chart(dados_longos)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("Data:T", title="Data"),
            y=alt.Y("Valor:Q", title=titulo_eixo_y),
            color=alt.Color("Setor:N", legend=alt.Legend(title="Setor")),
            tooltip=[
                alt.Tooltip("Data:T", title="Data"),
                alt.Tooltip("Setor:N", title="Setor"),
                alt.Tooltip("Valor:Q", title="Valor", format=".2f"),
            ],
        )
        .properties(height=480)
        .add_params(zoom_x)
    )

    st.altair_chart(chart, use_container_width=True)


def grafico_barras_setor(df_setor, coluna_valor, titulo_eixo_x="% acima da média"):
    """
    Gráfico de barras horizontais para ranking setorial atual.
    """
    if df_setor.empty or coluna_valor not in df_setor.columns:
        st.info("Sem dados setoriais suficientes para o ranking.")
        return

    dados = df_setor[["setor", coluna_valor]].dropna().copy()

    chart = (
        alt.Chart(dados)
        .mark_bar()
        .encode(
            y=alt.Y("setor:N", sort="-x", title="Setor"),
            x=alt.X(f"{coluna_valor}:Q", title=titulo_eixo_x),
            tooltip=[
                alt.Tooltip("setor:N", title="Setor"),
                alt.Tooltip(f"{coluna_valor}:Q", title=coluna_valor, format=".2f"),
            ],
        )
        .properties(height=420)
        .interactive()
    )

    st.altair_chart(chart, use_container_width=True)


def formatar_qtd_acima(ultima, media):
    """
    Formata a quantidade absoluta de ativos acima de uma média móvel.
    Exemplo: 21 de 83 ativos.
    """
    qtd = ultima.get(f"Qtd acima MM{media}")
    base = ultima.get(f"Base válida MM{media}")

    if pd.isna(qtd) or pd.isna(base) or base == 0:
        return "N/D"

    return f"{int(qtd)} de {int(base)} ativos"


def exibir_quadro_regras_regime():
    """
    Exibe o quadro explicativo dos critérios usados para classificar o regime.
    """
    st.markdown("### Critérios usados para definir o regime")

    st.info(
        """
        **O regime é definido a partir da participação dos ativos do Ibovespa acima das médias móveis de 20, 50 e 200 períodos.**

        - **Risk-on:** MM20 ≥ 60%, MM50 ≥ 55% e MM200 ≥ 50%.  
          Indica mercado com boa participação interna no curto, médio e longo prazo.

        - **Risk-off:** MM20 < 35%, MM50 < 40% e MM200 < 45%.  
          Indica mercado com baixa participação interna e fraqueza estrutural.

        - **Atenção:** MM20 < 40% e MM50 ≥ 50%.  
          Indica perda de força no curto prazo, mas com estrutura intermediária ainda resistente.

        - **Repique técnico:** MM20 ≥ 60% e MM50 < 45%.  
          Indica melhora de curto prazo, mas ainda sem confirmação intermediária.

        - **Neutro:** usado quando nenhuma das condições acima é atendida ou quando ainda não há dados suficientes.
        """
    )

def main():
    st.set_page_config(
        page_title="Market Breadth ELITE Setorial - Ibovespa",
        layout="wide"
    )

    st.title("Market Breadth ELITE - Ibovespa")
    st.caption("Amplitude de mercado com MM20, MM50, MM200, setores do IBOV, Advance/Decline e divergências.")

    with st.sidebar:
        st.header("Configurações")

        periodo = st.selectbox(
            "Período histórico",
            ["1y", "2y", "5y", "10y"],
            index=1
        )

        fonte_carteira = st.radio(
            "Fonte da carteira",
            [
                "Buscar automaticamente na B3",
                "Usar lista fallback editável"
            ],
            index=0
        )

    if fonte_carteira == "Buscar automaticamente na B3":
        try:
            carteira = buscar_carteira_ibov_b3()
            st.success(f"Carteira carregada da B3: {len(carteira)} ativos encontrados.")
        except Exception as erro:
            st.warning("Não foi possível buscar a carteira na B3. Usando fallback editável.")
            with st.expander("Detalhe técnico", expanded=False):
                st.code(str(erro), language="text")

            texto = st.text_area(
                "Lista fallback de tickers",
                value=", ".join(FALLBACK_TICKERS),
                height=180
            )
            carteira = criar_carteira_manual(texto)
    else:
        texto = st.text_area(
            "Lista fallback de tickers",
            value=", ".join(FALLBACK_TICKERS),
            height=180
        )
        carteira = criar_carteira_manual(texto)

    carteira = aplicar_setores(carteira)

    with st.expander("Carteira usada no cálculo", expanded=False):
        st.dataframe(carteira, width="stretch")

    tickers = carteira["ticker_yahoo"].dropna().drop_duplicates().tolist()

    if st.button("Atualizar painel", type="primary"):
        with st.spinner("Baixando dados e calculando indicadores..."):
            fechamentos = baixar_precos_yahoo(tickers, periodo)
            breadth = calcular_breadth(fechamentos, carteira)
            breadth_setor = calcular_breadth_por_setor(fechamentos, carteira)
            ad_line = calcular_advance_decline(fechamentos)
            tabela = calcular_tabela_ativos(fechamentos, carteira)
            ibov = baixar_ibov(periodo)

        if fechamentos.empty or breadth.empty:
            st.error("Não foi possível calcular. Verifique conexão, tickers ou bloqueio do Yahoo.")
            return

        breadth_valido = breadth.dropna(subset=["% acima MM20"], how="all")

        if breadth_valido.empty:
            st.error("Ainda não há dados suficientes para calcular o breadth.")
            return

        ultima = breadth_valido.iloc[-1]
        data_ultima = breadth_valido.index[-1].strftime("%d/%m/%Y")

        regime, leitura_regime = classificar_regime(ultima)
        divergencia = detectar_divergencia(ibov, breadth)

        st.subheader(f"Leitura mais recente - {data_ultima}")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Regime", regime)
        col2.metric("Acima da MM20", formatar_pct(ultima["% acima MM20"]))
        col3.metric("Acima da MM50", formatar_pct(ultima["% acima MM50"]))
        col4.metric("Acima da MM200", formatar_pct(ultima["% acima MM200"]))

        colq1, colq2, colq3, colq4 = st.columns(4)
        colq1.metric("Base total válida", f"{int(ultima['Total ativos válidos'])} ativos")
        colq2.metric("Qtd acima da MM20", formatar_qtd_acima(ultima, 20))
        colq3.metric("Qtd acima da MM50", formatar_qtd_acima(ultima, 50))
        colq4.metric("Qtd acima da MM200", formatar_qtd_acima(ultima, 200))

        st.info(leitura_regime)
        st.warning(divergencia)

        with st.expander("Ver regras e critérios usados para definir o regime", expanded=True):
            exibir_quadro_regras_regime()

        st.divider()

        st.caption(
            "Dica de navegação nos gráficos: use o scroll do mouse para aproximar/afastar no eixo temporal; "
            "arraste para navegar pelo período; dê duplo clique para restaurar a visualização completa."
        )

        st.subheader("Breadth percentual simples")
        grafico_medias_coloridas(
            breadth,
            ["% acima MM20", "% acima MM50", "% acima MM200"],
            titulo_eixo_y="% de ativos acima da média"
        )

        colunas_ponderadas = [
            c for c in [
                "% ponderado acima MM20",
                "% ponderado acima MM50",
                "% ponderado acima MM200"
            ]
            if c in breadth.columns
        ]

        if colunas_ponderadas:
            st.subheader("Breadth ponderado pelo peso no IBOV")
            grafico_medias_coloridas(
                breadth,
                colunas_ponderadas,
                titulo_eixo_y="% ponderado acima da média"
            )

        st.subheader("Quantidade de ativos acima das médias")
        grafico_medias_coloridas(
            breadth,
            ["Qtd acima MM20", "Qtd acima MM50", "Qtd acima MM200"],
            titulo_eixo_y="Quantidade de ativos"
        )

        st.divider()

        st.subheader("Breadth por setor do IBOV")
        st.caption("Mostra quais setores possuem maior participação de ativos acima das médias móveis.")

        if not breadth_setor.empty:
            col_setor1, col_setor2 = st.columns(2)

            with col_setor1:
                st.markdown("**Ranking setorial pela MM20**")
                grafico_barras_setor(
                    breadth_setor,
                    "% acima MM20",
                    titulo_eixo_x="% de ativos acima da MM20"
                )

            with col_setor2:
                st.markdown("**Ranking setorial pela MM50**")
                grafico_barras_setor(
                    breadth_setor,
                    "% acima MM50",
                    titulo_eixo_x="% de ativos acima da MM50"
                )

            st.markdown("**Tabela setorial completa**")
            st.dataframe(
                breadth_setor.style.format({
                    "% acima MM20": "{:.1f}%",
                    "% acima MM50": "{:.1f}%",
                    "% acima MM200": "{:.1f}%",
                    "% ponderado acima MM20": "{:.1f}%",
                    "% ponderado acima MM50": "{:.1f}%",
                    "% ponderado acima MM200": "{:.1f}%",
                }),
                width="stretch"
            )

            media_setorial = st.selectbox(
                "Escolha a média para ver o histórico setorial",
                [20, 50, 200],
                index=0
            )

            historico_setorial = calcular_historico_breadth_setorial(
                fechamentos,
                carteira,
                media=media_setorial
            )

            st.markdown(f"**Histórico setorial: % de ativos acima da MM{media_setorial}**")
            grafico_setorial_linhas(
                historico_setorial,
                titulo_eixo_y=f"% acima da MM{media_setorial}"
            )

            st.download_button(
                "Baixar breadth por setor em CSV",
                data=breadth_setor.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"),
                file_name="breadth_setorial_ibov.csv",
                mime="text/csv"
            )
        else:
            st.info("Não foi possível calcular o breadth setorial.")

        st.divider()

        st.subheader("Advance/Decline Line aproximada")
        grafico_linha_simples(
            ad_line,
            ["Advance/Decline Line"],
            titulo_eixo_y="Linha A/D acumulada"
        )

        if not ibov.empty:
            st.subheader("IBOV e médias móveis")
            grafico_medias_coloridas(
                ibov,
                ["IBOV", "MM20", "MM50", "MM200"],
                titulo_eixo_y="Pontos do IBOV"
            )

        st.divider()

        st.subheader("Ranking por ativo")
        st.caption("Ordenado pela distância percentual em relação à MM20.")

        st.dataframe(
            tabela.style.format({
                "participacao_pct": "{:.3f}",
                "ultimo_fechamento": "{:.2f}",
                "retorno_5d_pct": "{:.2f}%",
                "retorno_21d_pct": "{:.2f}%",
                "MM20": "{:.2f}",
                "MM50": "{:.2f}",
                "MM200": "{:.2f}",
                "dist_MM20_pct": "{:.2f}%",
                "dist_MM50_pct": "{:.2f}%",
                "dist_MM200_pct": "{:.2f}%",
            }),
            width="stretch"
        )

        st.download_button(
            "Baixar breadth em CSV",
            data=breadth.to_csv(sep=";", decimal=",", index=True).encode("utf-8-sig"),
            file_name="market_breadth_ibov_elite.csv",
            mime="text/csv"
        )

        st.download_button(
            "Baixar ranking por ativo em CSV",
            data=tabela.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"),
            file_name="ranking_ativos_ibov_elite.csv",
            mime="text/csv"
        )

        st.download_button(
            "Baixar Advance/Decline em CSV",
            data=ad_line.to_csv(sep=";", decimal=",", index=True).encode("utf-8-sig"),
            file_name="advance_decline_ibov.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
