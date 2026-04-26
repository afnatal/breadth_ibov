
import base64
import json
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import altair as alt

# (restante do código igual até gráficos...)

# --- FUNÇÃO PRINCIPAL COM GRÁFICOS ALTERADOS ---
def plot_breadth(breadth):
    df_plot = breadth[["% acima MM20", "% acima MM50", "% acima MM200"]].reset_index()
    df_plot = df_plot.melt("Date", var_name="Média", value_name="Valor")

    color_scale = alt.Scale(
        domain=["% acima MM20", "% acima MM50", "% acima MM200"],
        range=["green", "yellow", "red"]
    )

    chart = alt.Chart(df_plot).mark_line().encode(
        x="Date:T",
        y="Valor:Q",
        color=alt.Color("Média:N", scale=color_scale)
    ).properties(
        width="container",
        height=400
    )

    st.altair_chart(chart, use_container_width=True)


def plot_qtd(breadth):
    df_plot = breadth[["Qtd acima MM20", "Qtd acima MM50", "Qtd acima MM200"]].reset_index()
    df_plot = df_plot.melt("Date", var_name="Média", value_name="Valor")

    color_scale = alt.Scale(
        domain=["Qtd acima MM20", "Qtd acima MM50", "Qtd acima MM200"],
        range=["green", "yellow", "red"]
    )

    chart = alt.Chart(df_plot).mark_line().encode(
        x="Date:T",
        y="Valor:Q",
        color=alt.Color("Média:N", scale=color_scale)
    ).properties(
        width="container",
        height=400
    )

    st.altair_chart(chart, use_container_width=True)

# OBS: resto do código original mantido, apenas substituir chamadas de st.line_chart por:
# plot_breadth(breadth)
# plot_qtd(breadth)
