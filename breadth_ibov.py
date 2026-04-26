"""
Market Breadth PRO - Ibovespa
Versão corrigida

Correções desta versão:
- Corrige o aviso do Streamlit trocando use_container_width=True por width="stretch";
- Melhora a busca da carteira teórica do Ibovespa na B3;
- Usa requisição com payload em Base64, que é o formato normalmente aceito pelo serviço da B3;
- Mantém fallback editável caso a B3 bloqueie ou retorne HTML em vez de JSON;
- Permite usar lista manual com tickers com ou sem ".SA";
- Calcula breadth por MM20, MM50 e MM200;
- Mostra gráficos, ranking por ativo e exportação CSV.

Como executar:
1) Instale as dependências:
   pip install yfinance pandas streamlit requests matplotlib openpyxl

2) Rode:
   streamlit run breadth_ibov_pro_corrigido.py
"""

import base64
import json
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import yfinance as yf


# Fallback editável. Usado somente se a B3 não responder corretamente.
# Você pode alterar essa lista dentro da própria aplicação.
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
    """
    Monta a URL usada pelo serviço público da B3 para carteira teórica.

    A B3 costuma receber os parâmetros em JSON codificado em Base64.
    """
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


def _parse_percentual_b3(valor):
    """Converte percentual brasileiro da B3, ex.: '2,741', para float 2.741."""
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
    """
    Converte PETR4 em PETR4.SA.
    Mantém PETR4.SA se o usuário já digitou no padrão Yahoo.
    """
    ticker = str(ticker).strip().upper().replace(" ", "")

    if not ticker:
        return None

    if ticker.endswith(".SA"):
        return ticker

    return f"{ticker}.SA"


def criar_carteira_manual(texto):
    """
    Cria uma carteira a partir de texto colado pelo usuário.
    Aceita separação por vírgula, ponto e vírgula ou quebra de linha.
    """
    tickers = []

    texto = texto.replace(";", ",").replace("\n", ",")

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
    """
    Busca a carteira teórica atual do Ibovespa diretamente na B3.

    Retorna DataFrame com colunas:
    codigo, ticker_yahoo, acao, tipo, quantidade_teorica, participacao_pct
    """
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

    tentativas = []

    # 1) Formato moderno com payload Base64
    for language in ["pt-br", "en-us"]:
        tentativas.append(montar_url_b3(language=language))

    # 2) Formato antigo, mantido como tentativa adicional
    tentativas.extend([
        "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/IBOV?language=pt-br&pageNumber=1&pageSize=200",
        "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/IBOV?language=pt-br",
    ])

    ultimo_erro = None

    for url in tentativas:
        try:
            resposta = requests.get(url, headers=headers, timeout=30)
            resposta.raise_for_status()

            content_type = resposta.headers.get("Content-Type", "")

            # Quando a B3 bloqueia, ela pode devolver HTML.
            if "json" not in content_type.lower() and not resposta.text.strip().startswith("{"):
                raise RuntimeError(
                    "A B3 não retornou JSON. Possível bloqueio temporário ou alteração no serviço."
                )

            dados = resposta.json()
            resultados = dados.get("results", [])

            if not resultados:
                raise RuntimeError("A B3 retornou JSON, mas sem lista de ativos em 'results'.")

            linhas = []

            for item in resultados:
                codigo = (
                    item.get("cod")
                    or item.get("codigo")
                    or item.get("code")
                    or item.get("symbol")
                )

                if not codigo:
                    continue

                codigo = str(codigo).strip().upper()

                # Remove linhas agregadas ou inválidas.
                if codigo in ["IBOV", "TOTAL", "QUANTIDADE TEÓRICA TOTAL"]:
                    continue

                # Códigos válidos da B3 costumam ter no mínimo 5 caracteres.
                if len(codigo) < 5:
                    continue

                linhas.append({
                    "codigo": codigo,
                    "ticker_yahoo": f"{codigo}.SA",
                    "acao": item.get("asset") or item.get("acao") or item.get("companyName"),
                    "tipo": item.get("type") or item.get("tipo"),
                    "quantidade_teorica": item.get("theoricalQty") or item.get("qtdeTeorica"),
                    "participacao_pct": _parse_percentual_b3(item.get("part") or item.get("partAcum")),
                })

            df = pd.DataFrame(linhas)

            if not df.empty:
                df = df.drop_duplicates(subset=["codigo"]).sort_values("codigo").reset_index(drop=True)
                return df

            raise RuntimeError("A resposta da B3 não continha ativos válidos.")

        except Exception as erro:
            ultimo_erro = erro
            continue

    raise RuntimeError(f"Não foi possível buscar a carteira do IBOV na B3. Último erro: {ultimo_erro}")


@st.cache_data(ttl=30 * 60)
def baixar_precos_yahoo(tickers, periodo="2y"):
    """
    Baixa preços ajustados do Yahoo Finance.
    Retorna DataFrame de fechamentos.
    """
    if not tickers:
        return pd.DataFrame()

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

    fechamentos = fechamentos.dropna(how="all")
    return fechamentos


def calcular_breadth(fechamentos, medias=(20, 50, 200)):
    """
    Calcula:
    - quantidade de ativos acima de cada média;
    - percentual de ativos acima de cada média;
    - quantidade válida por data.
    """
    resultado = pd.DataFrame(index=fechamentos.index)
    ativos_validos = fechamentos.notna().sum(axis=1)
    resultado["Total ativos válidos"] = ativos_validos

    for media in medias:
        mm = fechamentos.rolling(media).mean()
        acima = fechamentos > mm

        # Conta somente ativos que possuem fechamento e média calculada na data.
        base_valida = fechamentos.notna() & mm.notna()

        qtd_acima = acima.where(base_valida).sum(axis=1)
        qtd_validos_media = base_valida.sum(axis=1)

        resultado[f"Qtd acima MM{media}"] = qtd_acima
        resultado[f"Base válida MM{media}"] = qtd_validos_media

        # Evita ZeroDivisionError quando ainda não há base válida suficiente,
        # por exemplo, nos primeiros 199 pregões para MM200.
        qtd_validos_media_seguro = qtd_validos_media.replace(0, pd.NA)
        resultado[f"% acima MM{media}"] = (qtd_acima / qtd_validos_media_seguro * 100)

    return resultado


def calcular_tabela_ativos(fechamentos, carteira_b3):
    """
    Cria tabela com último fechamento, médias móveis e distância percentual para cada ativo.
    """
    linhas = []

    for ticker in fechamentos.columns:
        serie = fechamentos[ticker].dropna()

        if serie.empty:
            continue

        fechamento = serie.iloc[-1]

        linha = {
            "ticker_yahoo": ticker,
            "codigo": ticker.replace(".SA", ""),
            "ultimo_fechamento": fechamento,
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
        carteira_b3[["codigo", "acao", "tipo", "participacao_pct"]],
        on="codigo",
        how="left"
    )

    colunas = [
        "codigo", "ticker_yahoo", "acao", "tipo", "participacao_pct",
        "ultimo_fechamento",
        "MM20", "acima_MM20", "dist_MM20_pct",
        "MM50", "acima_MM50", "dist_MM50_pct",
        "MM200", "acima_MM200", "dist_MM200_pct",
    ]

    return df[colunas].sort_values("dist_MM20_pct", ascending=False)


@st.cache_data(ttl=30 * 60)
def calcular_ibov(periodo="2y"):
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
    df["MM20"] = df["IBOV"].rolling(20).mean()
    df["MM50"] = df["IBOV"].rolling(50).mean()
    df["MM200"] = df["IBOV"].rolling(200).mean()

    return df


def converter_df_para_csv(df):
    return df.to_csv(sep=";", decimal=",", index=True).encode("utf-8-sig")


def main():
    st.set_page_config(
        page_title="Market Breadth PRO - Ibovespa",
        layout="wide"
    )

    st.title("Market Breadth PRO - Ibovespa")
    st.caption("Breadth baseado em ativos acima das médias móveis de 20, 50 e 200 períodos.")

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

        st.divider()

        st.caption("Caso a B3 esteja indisponível, use a lista fallback editável.")

    carteira_b3 = pd.DataFrame()

    if fonte_carteira == "Buscar automaticamente na B3":
        try:
            carteira_b3 = buscar_carteira_ibov_b3()
            st.success(f"Carteira atual carregada da B3: {len(carteira_b3)} ativos encontrados.")
        except Exception as erro:
            st.warning("Não foi possível buscar a carteira na B3.")
            st.info(
                "Vou carregar a lista fallback editável para que a aplicação continue funcionando. "
                "Você pode revisar os tickers antes de atualizar o breadth."
            )

            with st.expander("Detalhe técnico da falha da B3", expanded=False):
                st.code(str(erro), language="text")

            tickers_texto = st.text_area(
                "Lista fallback de tickers",
                value=", ".join(FALLBACK_TICKERS),
                height=180
            )

            carteira_b3 = criar_carteira_manual(tickers_texto)

    else:
        tickers_texto = st.text_area(
            "Lista fallback de tickers",
            value=", ".join(FALLBACK_TICKERS),
            height=180
        )

        carteira_b3 = criar_carteira_manual(tickers_texto)

    tickers = carteira_b3["ticker_yahoo"].dropna().drop_duplicates().tolist()

    with st.expander("Ver carteira utilizada no cálculo", expanded=False):
        st.dataframe(carteira_b3, width="stretch")

    if st.button("Atualizar breadth", type="primary"):
        with st.spinner("Baixando dados do Yahoo Finance e calculando indicadores..."):
            fechamentos = baixar_precos_yahoo(tickers, periodo)
            breadth = calcular_breadth(fechamentos)
            tabela_ativos = calcular_tabela_ativos(fechamentos, carteira_b3)
            ibov = calcular_ibov(periodo)

        if breadth.empty:
            st.error("Não foi possível calcular o breadth. Verifique sua conexão ou os tickers.")
            return

        breadth_valido = breadth.dropna(subset=["% acima MM20"], how="all")

        if breadth_valido.empty:
            st.error(
                "Ainda não há dados suficientes para calcular as médias. "
                "Tente aumentar o período histórico ou revisar os tickers."
            )
            return

        ultima = breadth_valido.iloc[-1]
        data_ultima = breadth_valido.index[-1].strftime("%d/%m/%Y")

        st.subheader(f"Leitura mais recente - {data_ultima}")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Ativos válidos", int(ultima["Total ativos válidos"]))
        def formatar_pct(valor):
            if pd.isna(valor):
                return "N/D"
            return f"{valor:.1f}%"

        col2.metric("Acima da MM20", formatar_pct(ultima["% acima MM20"]))
        col3.metric("Acima da MM50", formatar_pct(ultima["% acima MM50"]))
        col4.metric("Acima da MM200", formatar_pct(ultima["% acima MM200"]))

        st.divider()

        st.subheader("Breadth percentual")
        st.line_chart(
            breadth[[
                "% acima MM20",
                "% acima MM50",
                "% acima MM200"
            ]],
            width="stretch"
        )

        st.subheader("Quantidade de ativos acima das médias")
        st.line_chart(
            breadth[[
                "Qtd acima MM20",
                "Qtd acima MM50",
                "Qtd acima MM200"
            ]],
            width="stretch"
        )

        if not ibov.empty:
            st.subheader("IBOV e médias móveis")
            st.line_chart(
                ibov[["IBOV", "MM20", "MM50", "MM200"]],
                width="stretch"
            )

        st.divider()

        st.subheader("Tabela por ativo")
        st.caption("Ranking ordenado pela distância percentual em relação à MM20.")

        st.dataframe(
            tabela_ativos.style.format({
                "participacao_pct": "{:.3f}",
                "ultimo_fechamento": "{:.2f}",
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
            data=converter_df_para_csv(breadth),
            file_name="market_breadth_ibov_pro.csv",
            mime="text/csv"
        )

        st.download_button(
            "Baixar tabela de ativos em CSV",
            data=tabela_ativos.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig"),
            file_name="ativos_ibov_breadth_pro.csv",
            mime="text/csv"
        )

        st.info(
            "Leitura prática: MM20 mede força curta, MM50 mede tendência intermediária, "
            "MM200 mede saúde estrutural. Divergências entre IBOV subindo e breadth caindo "
            "costumam indicar perda de participação interna."
        )


if __name__ == "__main__":
    main()
