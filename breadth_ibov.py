"""
Market Breadth ELITE - Ibovespa

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


def main():
    st.set_page_config(
        page_title="Market Breadth ELITE - Ibovespa",
        layout="wide"
    )

    st.title("Market Breadth ELITE - Ibovespa")
    st.caption("Amplitude de mercado com MM20, MM50, MM200, Advance/Decline e divergências.")

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

    with st.expander("Carteira usada no cálculo", expanded=False):
        st.dataframe(carteira, width="stretch")

    tickers = carteira["ticker_yahoo"].dropna().drop_duplicates().tolist()

    if st.button("Atualizar painel", type="primary"):
        with st.spinner("Baixando dados e calculando indicadores..."):
            fechamentos = baixar_precos_yahoo(tickers, periodo)
            breadth = calcular_breadth(fechamentos, carteira)
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

        st.info(leitura_regime)
        st.warning(divergencia)

        st.divider()

        st.subheader("Breadth percentual simples")
        st.line_chart(
            breadth[["% acima MM20", "% acima MM50", "% acima MM200"]],
            width="stretch"
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
            st.line_chart(
                breadth[colunas_ponderadas],
                width="stretch"
            )

        st.subheader("Quantidade de ativos acima das médias")
        st.line_chart(
            breadth[["Qtd acima MM20", "Qtd acima MM50", "Qtd acima MM200"]],
            width="stretch"
        )

        st.subheader("Advance/Decline Line aproximada")
        st.line_chart(
            ad_line[["Advance/Decline Line"]],
            width="stretch"
        )

        if not ibov.empty:
            st.subheader("IBOV e médias móveis")
            st.line_chart(
                ibov[["IBOV", "MM20", "MM50", "MM200"]],
                width="stretch"
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
