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
        
        # Flag: indica se há um backup real para comparar lotes.
        # Sem baseline, não é possível afirmar que entrou produto novo.
        tem_baseline_lotes = not df_est_antigo.empty
        
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
                #    Só é válida se houver um backup real para comparar (tem_baseline_lotes).
                #    Sem baseline (ex: virada de mês com backups limpos), considera False
                #    para não atualizar a data indevidamente.
                conj_atual = lotes_atual.get(ean, set())
                conj_antigo = lotes_antigo.get(ean, set())
                lote_diferente_entrou = tem_baseline_lotes and len(conj_atual - conj_antigo) > 0
                
                # C) Validação principal:
                #    Só atualiza para hoje se há evidência REAL de entrada
                #    (estoque subiu E lote novo confirmado por comparação com backup)
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
    para comparação de lotes com o estado atual.

    Estratégia:
    - Os backups são salvos com sufixo de data/hora: ESTOQUE_DD-MM-YYYY_HHhMMm.csv
    - Busca todos os backups existentes (ESTOQUE* e ESTOQUE_Matriz*).
    - Exclui apenas o arquivo mais recente de hoje (que foi gerado na execução atual).
    - Retorna os arquivos do backup imediatamente anterior (pode ser de hoje ou de dia anterior).
    """
    dir_backups = os.path.join('imports', 'backups')

    # Padrão corrigido: backups têm sufixo de data/hora (ex: ESTOQUE_08-05-2026_11h30m.csv)
    padroes = [
        os.path.join(dir_backups, '*', '*', 'ESTOQUE_*.csv'),
        os.path.join(dir_backups, '*', '*', 'ESTOQUE_Matriz_*.csv'),
    ]

    todos_arquivos = []
    for padrao in padroes:
        todos_arquivos.extend(glob.glob(padrao))

    if not todos_arquivos:
        return []

    # Ordena por data de modificação (mais antigo → mais recente)
    todos_arquivos.sort(key=os.path.getmtime)

    # Identifica e remove o arquivo mais recente de cada tipo (gerado na execução atual)
    # para que a comparação seja com o estado ANTERIOR a esta execução.
    arquivos_estoque    = [f for f in todos_arquivos if 'Matriz' not in os.path.basename(f)]
    arquivos_matriz     = [f for f in todos_arquivos if 'Matriz' in os.path.basename(f)]

    resultado = []
    # Pega todos exceto o último de cada tipo (o mais recente = execução atual)
    if len(arquivos_estoque) > 1:
        resultado.extend(arquivos_estoque[:-1])
    if len(arquivos_matriz) > 1:
        resultado.extend(arquivos_matriz[:-1])

    # Se só há um arquivo de cada tipo (primeira execução real), não há baseline
    return resultado