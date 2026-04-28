import pandas as pd

def extrair_preco_custo(df_estoque):
    """
    Extrai o preço de custo (índice 5) mantendo o formato original string (ex: 15,20).
    """
    INDICE_EAN = 1
    INDICE_PRECO = 5 

    try:
        # 1. Seleção e Cópia
        df_custo = df_estoque[[INDICE_EAN, INDICE_PRECO]].copy()
        df_custo.columns = ['EAN', 'Preço Custo']
        
        # 2. Limpeza do EAN (sempre necessária)
        df_custo['EAN'] = df_custo['EAN'].astype(str).str.strip()
        
        # 3. Tratamento do Preço como TEXTO EXATO
        # Forçamos para string e limpamos apenas espaços nas pontas.
        # NÃO fazemos replace de vírgula nem conversão para numeric.
        df_custo['Preço Custo'] = df_custo['Preço Custo'].astype(str).str.strip()

        # Substituímos 'nan' (caso venha vazio no CSV) por '0,00' ou vazio
        df_custo['Preço Custo'] = df_custo['Preço Custo'].replace('nan', '0,00')

        # 4. Pega a última ocorrência (Preço mais recente)
        df_custo = df_custo.drop_duplicates(subset=['EAN'], keep='last')

        return df_custo

    except Exception as e:
        print(f"❌ Erro ao capturar preço de custo (texto): {e}")
        return None