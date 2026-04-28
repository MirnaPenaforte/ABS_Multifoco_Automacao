import ftplib
import os
from config.settings import Settings

def buscar_arquivos_ftp():
    """
    Realiza o download dos arquivos .csv do servidor FTP para a pasta imports.
    Busca nas pastas MULTIFOCO_DEMANDA/Matriz e MULTIFOCO_DEMANDA.
    Para arquivos na pasta Matriz, adiciona '_Matriz' ao nome.
    Retorna uma lista de caminhos locais dos arquivos baixados.
    """
    arquivos_baixados = []
    diretorios = [
        {"remote": "Matriz", "suffix": "_Matriz"},
        {"remote": "/", "suffix": ""}
    ]

    
    try:
        print(f"🔄 Conectando ao FTP: {Settings.FTP_HOST}:{Settings.FTP_PORT}")
        
        ftp = ftplib.FTP()
        try:
            ftp.connect(host=Settings.FTP_HOST, port=Settings.FTP_PORT, timeout=30)
            ftp.login(user=Settings.FTP_USER, passwd=Settings.FTP_PASS)
            ftp.set_pasv(True)  # Crucial para containers e firewalls
        except Exception as e:
            raise RuntimeError(f"Falha na conexão ou login FTP: {e}")
        
        try:
            for dir_info in diretorios:
                remote_dir = dir_info["remote"]
                suffix = dir_info["suffix"]
                
                print(f"📂 Verificando diretório FTP: {remote_dir}")
                try:
                    ftp.cwd('/') # Volta para a raiz para garantir caminho absoluto
                    ftp.cwd(remote_dir)
                    arquivos = ftp.nlst()
                    planilhas = [f for f in arquivos if f.upper().endswith('.CSV')]
                    
                    if not planilhas:
                        print(f"⚠️ Nenhum arquivo .csv encontrado em {remote_dir}.")
                        continue

                    for arquivo_remoto in planilhas:
                        # Adiciona o sufixo no nome do arquivo (antes da extensão)
                        nome_base, extensao = os.path.splitext(arquivo_remoto)
                        novo_nome = f"{nome_base}{suffix}{extensao}"
                        
                        caminho_local = os.path.join(Settings.IMPORTS_DIR, novo_nome)
                        print(f"⬇️ Baixando {arquivo_remoto} de {remote_dir} como {novo_nome}...")
                        
                        with open(caminho_local, 'wb') as f:
                            ftp.retrbinary(f"RETR {arquivo_remoto}", f.write)
                        
                        arquivos_baixados.append(caminho_local)
                except Exception as e:
                    print(f"⚠️ Erro ao acessar ou baixar de {remote_dir}: {e}")
                    continue
            
            if arquivos_baixados:
                print(f"✅ Total de {len(arquivos_baixados)} arquivo(s) baixado(s) com sucesso.")
            return arquivos_baixados
            
        finally:
            try:
                ftp.quit()
            except:
                try:
                    ftp.close()
                except:
                    pass

    except RuntimeError as re:
        print(f"❌ {re}")
        raise
    except Exception as e:
        print(f"❌ Erro inesperado na operação FTP: {e}")
        return arquivos_baixados