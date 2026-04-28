import pandas as pd

def processar_validade_estoque(df_estoque):
    """
    Pega a data de validade mais próxima (mínima) para cada EAN.
    """
    # VARIÁVEIS DE CONFIGURAÇÃO
    INDICE_EAN = 1
    INDICE_VALIDADE = 3

    try:
        #Organização de string
        df_estoque[INDICE_EAN] = df_estoque[INDICE_EAN].astype(str).str.strip()

        #Conversão de Data
        # O 'dayfirst=True' é vital para o padrão brasileiro (DD/MM/AAAA)
        # 'errors=coerce' transforma datas inválidas em NaT (Not a Time)
        df_estoque[INDICE_VALIDADE] = pd.to_datetime(
            df_estoque[INDICE_VALIDADE], 
            dayfirst=True, 
            errors='coerce'
        )

        # 1. Filtrar o que não tem data (opcional, dependendo da sua regra)
        # Se você quer ignorar quem não tem validade:
        # df_estoque = df_estoque.dropna(subset=[INDICE_VALIDADE])

        # 2. Agrupamento: Queremos a 'min' (data mais próxima/mais antiga)
        df_validade = df_estoque.groupby(INDICE_EAN)[INDICE_VALIDADE].min().reset_index()

        # 3. Renomear para a saída desejada
        df_validade.columns = ['EAN', 'Data Validade']

        df_validade['Data Validade'] = df_validade['Data Validade'].dt.strftime('%d/%m/%Y')

        # Opcional: Substituir valores vazios (NaT) por uma string amigável ou manter vazio
        df_validade['Data Validade'] = df_validade['Data Validade'].fillna('')

        return df_validade

    except Exception as e:
        print(f"❌ Erro ao processar validade: {e}")
        return None