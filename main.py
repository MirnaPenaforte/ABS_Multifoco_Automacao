import os
import sys
import pandas as pd
from core.read_Csv import ler_csv_sem_header
from core.Col_estoque import processar_estoque_agrupado
from core.Col_data_validade import processar_validade_estoque
from core.Col_Custo import extrair_preco_custo
from core.Col_Mes_atual import agrupar_vendas
from core.Col_faturamento_total import calcular_faturamento_atual
from core.Col_data_entrada import preencher_data_entrada
from utils.exporter_excel import gerar_relatorio_vendas
from utils.controler_import import arquivar_arquivos_importacao
from utils.api_client import enviar_ultimo_relatorio
from utils.ftp_client import buscar_arquivos_ftp
from utils.Disparo import iniciar_agendador

def main():
    diretorio_imports = 'imports'
    
    print("\n--- Iniciando sincronização com FTP ---")
    try:
        arquivos_baixados = buscar_arquivos_ftp()
        if not arquivos_baixados:
            print("⚠️ Sem arquivos novos para processar. Finalizando rotina.")
            return
    except RuntimeError:
        print("❌ Falha crítica no FTP: A rotina será retomada no próximo disparo agendado.")
        return

    # --- CARREGAMENTO E CONSOLIDAÇÃO DOS ARQUIVOS ---
    vendas_files = [f for f in arquivos_baixados if 'VENDA' in os.path.basename(f).upper()]
    estoque_files = [f for f in arquivos_baixados if 'ESTOQUE' in os.path.basename(f).upper()]

    def consolidar_dfs(lista_caminhos):
        dfs = []
        for path in lista_caminhos:
            df = ler_csv_sem_header(path)
            if df is not None:
                dfs.append(df)
        return pd.concat(dfs, ignore_index=True) if dfs else None

    df_vendas_bruto = consolidar_dfs(vendas_files)
    df_estoque_bruto = consolidar_dfs(estoque_files)

    if df_vendas_bruto is not None and df_estoque_bruto is not None:
        print(f"✅ Arquivos carregados e consolidados com sucesso: {len(vendas_files)} de vendas e {len(estoque_files)} de estoque.")


        # --- BACKUP DIÁRIO DE IMPORTAÇÕES ---
        print("Iniciando rotina de backup dos arquivos importados do dia...")
        arquivar_arquivos_importacao(diretorio_imports)

        # --- PROCESSAMENTOS INDIVIDUAIS ---
        estoque_final = processar_estoque_agrupado(df_estoque_bruto.copy())
        custo_final = extrair_preco_custo(df_estoque_bruto.copy())
        validade_final = processar_validade_estoque(df_estoque_bruto.copy())
        
        vendas_final = agrupar_vendas(df_vendas_bruto.copy())
        faturamento_final = calcular_faturamento_atual(df_vendas_bruto.copy())

        # --- CONSOLIDAÇÃO FINAL ---
        try:
            # 1. União dos dados pelo EAN
            # Utilizamos how='outer' para preservar EANs que só aparecem em vendas.csv
            df_final = pd.merge(estoque_final, custo_final, on='EAN', how='outer')
            df_final = pd.merge(df_final, validade_final, on='EAN', how='outer')
            df_final = pd.merge(df_final, vendas_final, on='EAN', how='outer')
            df_final = pd.merge(df_final, faturamento_final, on='EAN', how='outer')

            # 2. Adicionar Data de Entrada (dd/mm/aa)
            df_final = preencher_data_entrada(df_final)

            # 3. Limpeza de Nulos e Tipagem
            colunas_numericas = ['Estoque', 'Mês Atual', 'Faturamento Atual']
            df_final[colunas_numericas] = df_final[colunas_numericas].fillna(0)
            
            # Garantir formato inteiro para colunas de contagem
            df_final['Estoque'] = df_final['Estoque'].astype(int)
            df_final['Mês Atual'] = df_final['Mês Atual'].astype(int)
            df_final['Mês -1'] = df_final['Mês -1'].astype('Int64')
            
            # Para todo item cujo estoque for 0, o preço de custo passa a ser "0,001"
            estoque_zero = df_final['Estoque'] == 0
            df_final.loc[estoque_zero, 'Preço Custo'] = "0,001"
            
            # Itens restantes sem preço recebem formato "0,00"
            df_final['Preço Custo'] = df_final['Preço Custo'].fillna("0,00")
            
            # Garantia extra contra zeros inteiros salvos do processo
            df_final['Preço Custo'] = df_final['Preço Custo'].astype(str).replace('0', '0,00').replace('0.0', '0,00')

            # --- EXPORTAÇÃO E GESTÃO DE ARQUIVOS (Output) ---
            # Esta função cria as colunas vazias, salva na pasta /output 
            # e remove os arquivos mais antigos mantendo apenas os 4 últimos.
            gerar_relatorio_vendas(df_final)
            
            print("\n--- Fluxo finalizado: Relatório gerado e pasta /output organizada ---")
            
            # --- ENVIO PARA API ---
            print("\n--- Iniciando envio para a API ---")
            sucesso_envio = enviar_ultimo_relatorio()
            if sucesso_envio:
                print("✅ Relatório enviado com sucesso para a API!")
            else:
                print("❌ Falha ao enviar o relatório para a API.")
            
        except Exception as e:
            print(f"❌ Erro crítico no processamento final: {e}")
    else:
        print("❌ Erro fatal: Verifique se os arquivos VENDA.csv e ESTOQUE.csv estão na pasta /imports.")

if __name__ == "__main__":
    # Executa uma vez imediatamente ao iniciar
    main()
    
    # Inicia o agendador para os horários programados (08:00, 15:00, 20:00)
    iniciar_agendador(main)