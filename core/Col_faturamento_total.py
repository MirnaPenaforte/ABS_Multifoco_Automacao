import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calcular_faturamento_atual(df_vendas):
    """
    Soma a quantidade total por EAN e multiplica pelo ÚLTIMO preço encontrado.
    Gera as colunas 'Faturamento Atual' e 'Faturamento M-1'.
    """
    INDICE_CFOP = 0      # Coluna 1
    INDICE_DATA = 2
    INDICE_QTD = 5       # Coluna 6
    INDICE_PRECO_UN = 6  # Coluna 7
    INDICE_EAN = 7       # Coluna 8

    try:
        # 0. Filtrar CFOPs indesejados
        df_vendas[INDICE_CFOP] = df_vendas[INDICE_CFOP].astype(str).str.strip()
        df_vendas = df_vendas[~df_vendas[INDICE_CFOP].isin(['6202', '5202'])]

        # 1. Limpeza inicial do EAN
        df_vendas[INDICE_EAN] = df_vendas[INDICE_EAN].astype(str).str.strip()

        # 2. Tratamento Numérico
        # Quantidade como Inteiro
        df_vendas[INDICE_QTD] = pd.to_numeric(df_vendas[INDICE_QTD], errors='coerce').fillna(0).astype('int64')
        
        # Preço como Float (tratando o formato 25,10)
        df_vendas[INDICE_PRECO_UN] = (
            df_vendas[INDICE_PRECO_UN]
            .astype(str)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
        )
        df_vendas[INDICE_PRECO_UN] = pd.to_numeric(df_vendas[INDICE_PRECO_UN], errors='coerce').fillna(0.0)

        # Descartar linhas onde o preco_un é zero para não ser levado em conta na multiplicação
        df_vendas = df_vendas[df_vendas[INDICE_PRECO_UN] > 0]

        # Converte Data
        df_vendas['data_venda'] = pd.to_datetime(df_vendas[INDICE_DATA], format='%d/%m/%Y', errors='coerce')

        hoje = datetime.now()
        mes_atual = hoje.month
        ano_atual = hoje.year

        mes_passado_dt = hoje - relativedelta(months=1)
        mes_passado = mes_passado_dt.month
        ano_passado = mes_passado_dt.year

        mask_atual = (df_vendas['data_venda'].dt.month == mes_atual) & (df_vendas['data_venda'].dt.year == ano_atual)
        mask_passado = (df_vendas['data_venda'].dt.month == mes_passado) & (df_vendas['data_venda'].dt.year == ano_passado)

        # 3. Agrupamento com Duas Operações (Soma e Último)
        df_atual = df_vendas[mask_atual].groupby(INDICE_EAN).agg({
            INDICE_QTD: 'sum',
            INDICE_PRECO_UN: 'last'
        }).reset_index()

        df_passado = df_vendas[mask_passado].groupby(INDICE_EAN).agg({
            INDICE_QTD: 'sum',
            INDICE_PRECO_UN: 'last'
        }).reset_index()

        # 4. Cálculo do Faturamento
        df_atual['Faturamento Atual'] = df_atual[INDICE_QTD] * df_atual[INDICE_PRECO_UN]
        df_atual_final = df_atual[[INDICE_EAN, 'Faturamento Atual']].copy()
        df_atual_final.columns = ['EAN', 'Faturamento Atual']

        df_passado['Faturamento M-1'] = df_passado[INDICE_QTD] * df_passado[INDICE_PRECO_UN]
        df_passado_final = df_passado[[INDICE_EAN, 'Faturamento M-1']].copy()
        df_passado_final.columns = ['EAN', 'Faturamento M-1']

        # 5. Seleção Final
        df_final = pd.merge(df_atual_final, df_passado_final, on='EAN', how='outer')
        df_final['Faturamento Atual'] = df_final['Faturamento Atual'].fillna(0.0)

        return df_final

    except Exception as e:
        print(f"❌ Erro ao calcular faturamento agrupado: {e}")
        return None 