from pathlib import Path
from collections import Counter
import ctypes
from ctypes import wintypes
import os
import shutil
import time
import pymupdf
import zxingcpp
from PIL import Image
import pefile
import joblib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def obter_pasta_windows(csidl, fallback_nomes):
    """Obtém o caminho real das pastas especiais do Windows 11 (Imagens, Músicas, Vídeos, Documentos)."""
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    if ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0 and buf.value:
        return Path(buf.value)

    home = Path.home()
    for nome in fallback_nomes:
        for base in [home / "OneDrive", home]:
            caminho = base / nome
            if caminho.exists():
                return caminho
    return home / fallback_nomes[-1]


# --- PASTAS NATIVAS DO WINDOWS 11 ---
PASTA_ORIGEM = str(Path.home() / "Downloads")
PASTA_IMAGENS = obter_pasta_windows(0x0027, ["Imagens", "Pictures"])
PASTA_MUSICAS = obter_pasta_windows(0x000D, ["Músicas", "Music"])
PASTA_VIDEOS = obter_pasta_windows(0x000E, ["Vídeos", "Videos"])
PASTA_DOCUMENTOS = obter_pasta_windows(0x0005, ["Documentos", "Documents"])

DESTINOS_CATEGORIA = {
    "imagens": str(PASTA_IMAGENS),
    "musicas": str(PASTA_MUSICAS),
    "videos": str(PASTA_VIDEOS),
    "executaveis": str(PASTA_DOCUMENTOS / "executaveis"),
    "estudo": str(PASTA_DOCUMENTOS / "estudo"),
    "financeiro": str(PASTA_DOCUMENTOS / "financeiro"),
    "outros": str(PASTA_DOCUMENTOS / "outros"),
}

# --- REGRAS DE EXTENSÃO ---
EXTENSOES_ESTUDO = {".py", ".c", ".cpp", ".h", ".java", ".js", ".ts", ".sql", ".sh", ".ipynb"}
EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico"}
EXTENSOES_MUSICA = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}
EXTENSOES_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"}
EXTENSOES_EXECUTAVEL = {".exe", ".msi"}

IGNORAR_ARQUIVOS = {"desktop.ini", "thumbs.db"}
IGNORAR_EXTENSOES = {".tmp", ".crdownload", ".part", ".ini", ".pyc"}

# Carrega o modelo de Machine Learning usando o caminho absoluto da pasta do script
CAMINHO_MODELO = Path(__file__).resolve().parent / "modelo_ia.pkl"
modelo_ia = joblib.load(CAMINHO_MODELO)


def tem_codigo_barras_pdf(caminho_pdf):
    """Converte páginas do PDF em imagem e procura códigos de barras usando zxing-cpp."""
    try:
        doc = pymupdf.open(caminho_pdf)
        for pagina in doc:
            pix = pagina.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            codigos = zxingcpp.read_barcodes(img)
            if len(codigos) > 0:
                return True
    except Exception as e:
        print(f"Erro ao ler código de barras de {caminho_pdf}: {e}")
    return False


def extrair_texto_pdf(caminho_pdf):
    """Extrai o texto de um PDF para análise do ML."""
    texto = ""
    try:
        doc = pymupdf.open(caminho_pdf)
        for pagina in doc:
            texto += pagina.get_text() + " "
    except Exception as e:
        print(f"Erro ao extrair texto de {caminho_pdf}: {e}")
    return texto.strip()


def classificar_arquivo(caminho_arquivo):
    """Decide a categoria do arquivo usando regras + Machine Learning."""
    nome_arquivo = os.path.basename(caminho_arquivo)
    _, ext = os.path.splitext(nome_arquivo)
    ext = ext.lower()

    if ext in EXTENSOES_IMAGEM:
        print(f"[IMAGEM] {nome_arquivo} -> Imagens")
        return "imagens"

    if ext in EXTENSOES_MUSICA:
        print(f"[MÚSICA] {nome_arquivo} -> Músicas")
        return "musicas"

    if ext in EXTENSOES_VIDEO:
        print(f"[VÍDEO] {nome_arquivo} -> Vídeos")
        return "videos"

    if ext in EXTENSOES_EXECUTAVEL:
        print(f"[EXECUTÁVEL] {nome_arquivo} -> Documentos\\executaveis")
        return "executaveis"

    if ext in EXTENSOES_ESTUDO:
        print(f"[CÓDIGO] {nome_arquivo} -> Documentos\\estudo")
        return "estudo"

    if ext == ".pdf":
        if tem_codigo_barras_pdf(caminho_arquivo):
            print(f"[BOLETO DETECTADO] {nome_arquivo} -> Documentos\\financeiro")
            return "financeiro"

        texto = extrair_texto_pdf(caminho_arquivo)
        if texto:
            categoria_predita = modelo_ia.predict([texto])[0]
            destino = categoria_predita if categoria_predita in DESTINOS_CATEGORIA else "outros"
            print(f"[ML PDF] {nome_arquivo} -> {destino}")
            return destino
        print(f"[PDF VAZIO] {nome_arquivo} -> Documentos\\outros")
        return "outros"

    print(f"[OUTROS] {nome_arquivo} -> Documentos\\outros")
    return "outros"


def classificar_pasta(caminho_pasta):
    """Analisa o conteúdo de uma pasta para classificá-la sem desmontá-la."""
    votos = Counter()

    for raiz, pastas, arquivos in os.walk(caminho_pasta):
        if "__pycache__" in pastas or ".git" in pastas or ".venv" in pastas:
            print(f"[PASTA PROJETO] {os.path.basename(caminho_pasta)} -> Documentos\\estudo")
            return "estudo"

        for nome_arquivo in arquivos:
            if nome_arquivo.lower() in IGNORAR_ARQUIVOS:
                continue
            if os.path.splitext(nome_arquivo)[1].lower() in IGNORAR_EXTENSOES:
                continue

            caminho_item = os.path.join(raiz, nome_arquivo)
            categoria = classificar_arquivo(caminho_item)
            votos[categoria] += 1

    if not votos:
        return "outros"

    if votos["estudo"] > 0:
        print(f"[PASTA INTEIRA] {os.path.basename(caminho_pasta)} ({dict(votos)}) -> Documentos\\estudo")
        return "estudo"

    categoria_vencedora = votos.most_common(1)[0][0]
    print(f"[PASTA INTEIRA] {os.path.basename(caminho_pasta)} ({dict(votos)}) -> {categoria_vencedora}")
    return categoria_vencedora


def mover_item(caminho_origem, categoria):
    """Move o arquivo ou pasta para o destino correspondente no Windows."""
    pasta_destino = DESTINOS_CATEGORIA.get(categoria, DESTINOS_CATEGORIA["outros"])
    os.makedirs(pasta_destino, exist_ok=True)

    nome_item = os.path.basename(caminho_origem)
    caminho_final = os.path.join(pasta_destino, nome_item)

    contador = 1
    nome_base, ext = os.path.splitext(nome_item)
    while os.path.exists(caminho_final):
        caminho_final = os.path.join(pasta_destino, f"{nome_base}_{contador}{ext}")
        contador += 1

    shutil.move(caminho_origem, caminho_final)


def executar_varredura_inicial():
    """Organiza tudo o que já estiver na pasta Downloads ao iniciar."""
    if not os.path.exists(PASTA_ORIGEM):
        print(f"Pasta de origem não encontrada: {PASTA_ORIGEM}")
        return

    itens = os.listdir(PASTA_ORIGEM)
    processados = 0

    for item in itens:
        caminho_completo = os.path.join(PASTA_ORIGEM, item)

        if os.path.isdir(caminho_completo):
            categoria = classificar_pasta(caminho_completo)
            mover_item(caminho_completo, categoria)
            processados += 1
        elif os.path.isfile(caminho_completo):
            if item.lower() in IGNORAR_ARQUIVOS or os.path.splitext(item)[1].lower() in IGNORAR_EXTENSOES:
                continue
            categoria = classificar_arquivo(caminho_completo)
            mover_item(caminho_completo, categoria)
            processados += 1

    if processados == 0:
        print("Nenhum arquivo pendente na varredura inicial.")


# --- VIGIA EM TEMPO REAL ---
def aguardar_arquivo_liberar(caminho, tentativas=20):
    """Espera o navegador terminar de gravar o arquivo antes de mover."""
    for _ in range(tentativas):
        try:
            with open(caminho, "rb+"):
                return True
        except (OSError, PermissionError):
            time.sleep(1)
    return False


def processar_novo_evento(caminho_str):
    caminho = Path(caminho_str)
    if not caminho.exists():
        return

    # Garante que só atua na raiz de Downloads (não mexe dentro de subpastas)
    if caminho.parent.resolve() != Path(PASTA_ORIGEM).resolve():
        return

    nome = caminho.name
    if nome.lower() in IGNORAR_ARQUIVOS or caminho.suffix.lower() in IGNORAR_EXTENSOES:
        return

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
        processar_novo_evento(event.src_path)

    def on_moved(self, event):
        processar_novo_evento(event.dest_path)


if __name__ == "__main__":
    print(f"Vigiando:    {PASTA_ORIGEM}")
    print(f"Imagens:     {DESTINOS_CATEGORIA['imagens']}")
    print(f"Músicas:     {DESTINOS_CATEGORIA['musicas']}")
    print(f"Vídeos:      {DESTINOS_CATEGORIA['videos']}")
    print(f"Executáveis: {DESTINOS_CATEGORIA['executaveis']}")
    print(f"Estudo:      {DESTINOS_CATEGORIA['estudo']}\n")

    executar_varredura_inicial()

    observador = Observer()
    observador.schedule(ManipuladorDownloads(), PASTA_ORIGEM, recursive=False)
    observador.start()

    print("\n[ATIVO] Aguardando novos arquivos em Downloads... (Pressione Ctrl + C no terminal para encerrar)\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando o organizador...")
        observador.stop()

    observador.join()
    print("Organizador encerrado com sucesso.")