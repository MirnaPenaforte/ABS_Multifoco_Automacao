import pandas as pd
import os
import glob
from datetime import datetime

def preencher_data_entrada(df_final):
    """
    Atualiza a 'Data Entrada' baseada no ESTOQUE.csv.
    Verifica se houve aumento de estoque decorrente da entrada de um lote diferente 
    comparando com o último Estoque.csv arquivado.
    Se não, mantém a do arquivo XLSX anterior.
    """
    try:
        data_hoje = datetime.now().strftime('%d/%m/%Y')
        
        # 1. Obter o relatório XLSX anterior para pegar as datas e estoque totais mantidos
        diretorio_saida = 'output'
        #Busca recursivamente, já que os relatórios estão sendo organizados em pastas de Mês/Dia
        padrao_busca = os.path.join(diretorio_saida, "**", "*.xlsx")
        arquivos_xlsx = glob.glob(padrao_busca, recursive=True)
        
        # Filtra arquivos temporários gerados com o Excel aberto
        arquivos_xlsx = [f for f in arquivos_xlsx if not os.path.basename(f).startswith("~$")]
        
        df_anterior = None
        
        if arquivos_xlsx:
            arquivos_xlsx.sort(key=os.path.getmtime)
            # Pega o arquivo XLSX mais novo (o do processo anterior ao atual)
            arquivo_anterior_xlsx = arquivos_xlsx[-1] 
            df_anterior = pd.read_excel(arquivo_anterior_xlsx)
            
            if 'EAN' in df_anterior.columns:
                df_anterior['EAN'] = df_anterior['EAN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            if 'Estoque' in df_anterior.columns:
                df_anterior['Estoque'] = pd.to_numeric(df_anterior['Estoque'], errors='coerce').fillna(0)

        # 2. Ler os arquivos de ESTOQUE atuais (da pasta imports) — filial + Matriz
        # Conforme especificado: O lote está no índice [2] e o estoque em [4]
        dfs_estoque_atual = []
        for nome_arq in ['ESTOQUE.csv', 'ESTOQUE_Matriz.csv']:
            caminho = os.path.join('imports', nome_arq)
            if os.path.exists(caminho):
                try:
                    dfs_estoque_atual.append(pd.read_csv(caminho, header=None, sep=';', dtype=str))
                except Exception as e:
                    print(f"⚠️ Não foi possível ler {nome_arq}: {e}")
        df_est_atual = pd.concat(dfs_estoque_atual, ignore_index=True) if dfs_estoque_atual else pd.DataFrame()

        # 3. Ler os arquivos de ESTOQUE anteriores dos backups (filial + Matriz)
        dfs_estoque_antigo = []
        for caminho_antigo in _buscar_csvs_estoque_anteriores():
            if os.path.exists(caminho_antigo):
                try:
                    dfs_estoque_antigo.append(pd.read_csv(caminho_antigo, header=None, sep=';', dtype=str))
                except Exception as e:
                    print(f"⚠️ Não foi possível ler backup {caminho_antigo}: {e}")
        df_est_antigo = pd.concat(dfs_estoque_antigo, ignore_index=True) if dfs_estoque_antigo else pd.DataFrame()

        # Mapeando histórico de lotes: um dicionário para cada CSV com EAN -> Set de Lotes
        lotes_atual = _mapear_lotes(df_est_atual)   
        lotes_antigo = _mapear_lotes(df_est_antigo) 
        
        # Mapeando estado do XLSX passado:
        mapa_datas_antigas = {}
        mapa_estoque_antigo = {}
        if df_anterior is not None and not df_anterior.empty:
            for idx, row in df_anterior.iterrows():
                ean_str = str(row['EAN']).replace('.0', '').strip()
                mapa_datas_antigas[ean_str] = row.get('Data Entrada', data_hoje)
                mapa_estoque_antigo[ean_str] = row.get('Estoque', 0)

        # 4. Avaliar cada linha do dataframe final com as regras de negócio
        datas_entrada = []
        for idx, row in df_final.iterrows():
            ean = str(row['EAN']).replace('.0', '').strip()
            estoque_final_atual = float(row['Estoque']) if pd.notna(row['Estoque']) else 0
            
            data_decidida = data_hoje # Data padrão de entrada
            
            # Se já tínhamos esse EAN reportado, vamos verificar a regra
            if df_anterior is not None and ean in mapa_datas_antigas:
                data_antiga = mapa_datas_antigas[ean]
                estoque_antigo = float(mapa_estoque_antigo.get(ean, 0))
                
                # Regras: "verifica se o estoque subiu com a entrada de um lote diferente"
                # A) O estoque aumentou
                estoque_subiu = estoque_final_atual > estoque_antigo
                
                # B) A lista atual de lotes desse EAN tem algum lote que a do CSV antigo não tinha
                conj_atual = lotes_atual.get(ean, set())
                conj_antigo = lotes_antigo.get(ean, set())
                
                lote_diferente_entrou = len(conj_atual - conj_antigo) > 0
                
                # C) Validação principal:
                if estoque_subiu and lote_diferente_entrou:
                    data_decidida = data_hoje
                else:
                    data_decidida = data_antiga
            
            datas_entrada.append(data_decidida)
            
        df_final['Data Entrada'] = datas_entrada
        return df_final

    except Exception as e:
        print(f"❌ Erro ao cruzar lotes para identificar Data de Entrada: {e}")
        # Em caso de falha, assinala hoje para assegurar que não quebre pipeline
        df_final['Data Entrada'] = datetime.now().strftime('%d/%m/%Y')
        return df_final


def _mapear_lotes(df_estoque):
    """
    Constrói um dicionário EAN -> set(Lotes).
    Para encontrar se há novos lotes em circulação, usando os índices informados.
    Índice [1]: EAN
    Índice [2]: Referência do lote
    Índice [4]: Estoque em quantidade
    """
    mapa = {}
    if df_estoque.empty or len(df_estoque.columns) <= 2:
        return mapa
        
    for index, row in df_estoque.iterrows():
        try:
            ean = str(row[1]).replace('.0', '').strip()
            lote = str(row[2]).strip()
            
            if pd.notna(row[1]) and ean:
                if ean not in mapa:
                    mapa[ean] = set()
                mapa[ean].add(lote)
        except:
            pass
            
    return mapa


def _buscar_csv_estoque_anterior():
    """
    [DEPRECATED] Mantido para compatibilidade. Use _buscar_csvs_estoque_anteriores().
    """
    resultados = _buscar_csvs_estoque_anteriores()
    return resultados[0] if resultados else None


def _buscar_csvs_estoque_anteriores():
    """
    Busca os arquivos ESTOQUE*.csv de backup (filial e Matriz) feitos pelas importações diárias,
    em data anterior à de hoje, para comparação de lotes.
    Retorna uma lista de caminhos encontrados.
    """
    dir_backups = os.path.join('imports', 'backups')
    hoje_str = datetime.now().strftime('%d-%m-%Y')
    
    # Busca ESTOQUE.csv e ESTOQUE_Matriz*.csv nos backups
    padroes = [
        os.path.join(dir_backups, '*', '*', 'ESTOQUE.csv'),
        os.path.join(dir_backups, '*', '*', 'ESTOQUE_Matriz*.csv'),
    ]
    
    arquivos_antigos = []
    for padrao in padroes:
        for f in glob.glob(padrao):
            if hoje_str not in f:  # Exclui backups de hoje
                arquivos_antigos.append(f)
    
    if not arquivos_antigos:
        return []
    
    # Ordena por data de modificação e retorna os mais recentes
    arquivos_antigos.sort(key=os.path.getmtime)
    # Retorna os arquivos do backup mais recente (pode ser ESTOQUE + ESTOQUE_Matriz)
    return arquivos_antigos