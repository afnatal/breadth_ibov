# Market Breadth ELITE - Ibovespa

Aplicação em Streamlit para medir a amplitude de mercado do Ibovespa.

## Recursos

- Carteira atual do Ibovespa via B3
- Fallback manual editável
- Dados de preço via Yahoo Finance
- Percentual de ativos acima da MM20, MM50 e MM200
- Breadth ponderado pelo peso do IBOV, quando disponível
- Advance/Decline Line
- Divergência entre IBOV e breadth
- Regime de mercado
- Ranking por ativo
- Exportação CSV

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run breadth_ibov_elite.py
```

## Deploy no Streamlit Cloud

Main file path:

```text
breadth_ibov_elite.py
```
