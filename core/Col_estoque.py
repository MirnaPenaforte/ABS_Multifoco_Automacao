import pandas as pd

def processar_estoque_agrupado(df_estoque):
    """
    Agrupa EANs e soma o estoque usando índices configuráveis.
    """
    # --- CONFIGURAÇÃO MANUAL (Ajuste aqui) ---
    INDICE_EAN = 1     
    INDICE_ESTOQUE = 4 

    try:
        #Limpar espaços e garantir que o EAN seja string
        df_estoque[INDICE_EAN] = df_estoque[INDICE_EAN].astype(str).str.strip()

        # 1. Garantir que os dados de estoque sejam numéricos
        df_estoque[INDICE_ESTOQUE] = pd.to_numeric(df_estoque[INDICE_ESTOQUE], errors='coerce').fillna(0)

        # 2. Agrupamento e Soma
        # Agrupamos pelo índice do EAN e somamos a coluna de estoque
        df_agrupado = df_estoque.groupby(INDICE_EAN)[INDICE_ESTOQUE].sum().reset_index()

        # 3. Renomear para a saída final
        df_agrupado.columns = ['EAN', 'Estoque']

        return df_agrupado

    except Exception as e:
        print(f"❌ Erro na manipulação de estoque: {e}")
        return None