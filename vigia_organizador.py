import os
import time
from pathlib import Path
import joblib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Importa as funções e configurações já prontas do seu organizador.py
from organizador import (
    PASTA_ORIGEM,
    IGNORAR_ARQUIVOS,
    IGNORAR_EXTENSOES,
    classificar_arquivo,
    classificar_pasta,
    mover_item,
    executar_organizador,
)

# Garante que o modelo seja encontrado mesmo quando iniciado pelo Windows fora da pasta
DIRETORIO_SCRIPT = Path(__file__).resolve().parent
os.chdir(DIRETORIO_SCRIPT)


def aguardar_arquivo_liberar(caminho, tentativas=15):
    """Espera o navegador terminar de gravar o arquivo antes de tentar mover."""
    for _ in range(tentativas):
        try:
            # Tenta abrir em modo exclusivo; se o navegador ainda estiver baixando, falha
            with open(caminho, "rb+"):
                return True
        except (OSError, PermissionError):
            time.sleep(1)
    return False


def processar_caminho(caminho_str):
    caminho = Path(caminho_str)
    if not caminho.exists():
        return

    # Ignora itens que estão dentro de subpastas (age apenas no nível raiz de Downloads)
    if caminho.parent.resolve() != Path(PASTA_ORIGEM).resolve():
        return

    nome = caminho.name
    if nome.lower() in IGNORAR_ARQUIVOS or caminho.suffix.lower() in IGNORAR_EXTENSOES:
        return

    # Pequena pausa para garantir que downloads/extrações terminaram
    time.sleep(1.5)
    if not caminho.exists():
        return

    if caminho.is_dir():
        categoria = classificar_pasta(str(caminho))
        mover_item(str(caminho), categoria)
    elif caminho.is_file():
        if aguardar_arquivo_liberar(caminho):
            categoria = classificar_arquivo(str(caminho))
            mover_item(str(caminho), categoria)


class ManipuladorDownloads(FileSystemEventHandler):
    def on_created(self, event):
        processar_caminho(event.src_path)

    def on_moved(self, event):
        # Navegadores (Chrome/Edge/Brave) baixam como .crdownload e renomeiam ao concluir
        processar_caminho(event.dest_path)


if __name__ == "__main__":
    # 1. Faz uma varredura inicial no que já estiver parado em Downloads
    executar_organizador()

    # 2. Inicia o monitoramento contínuo em segundo plano
    observador = Observer()
    observador.schedule(ManipuladorDownloads(), PASTA_ORIGEM, recursive=False)
    observador.start()

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        observador.stop()
    observador.join()