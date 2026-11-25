#  Robô Organizador de Arquivos

Automação desenvolvida em Python utilizando técnicas de **Machine Learning** para classificar, categorizar e organizar arquivos locais de forma automática e inteligente.

##  Sobre o Projeto

Este projeto tem como objetivo eliminar a tarefa manual de triagem e movimentação de arquivos em diretórios locais (como Downloads ou Documentos). Através do processamento de texto e classificação automatizada, o script identifica o contexto de cada arquivo e o direciona para a pasta correspondente.

##  Funcionalidades

* **Classificação Automatizada:** Categorização inteligente baseada no nome e/ou conteúdo dos arquivos.
* **Processamento em Lote:** Leitura e organização simultânea de múltiplos arquivos.
* **Prevenção de Conflitos:** Tratamento seguro na movimentação e renomeação de arquivos no sistema operacional.
* **Alta Performance:** Execução leve e rápida utilizando modelos preditivos locais.

##  Tecnologias Utilizadas

* **Python 3.x**
* **Scikit-Learn / Machine Learning** (vetorização e classificação de texto)
* **Joblib** (persistência e carregamento rápido do modelo)
* **OS / Shutil / Pathlib** (manipulação de diretórios e arquivos no sistema)

##  Como Executar

### 1. Pré-requisitos
Certifique-se de ter o [Python](https://www.python.org/) instalado em sua máquina.

### 2. Clone o repositório
```bash
git clone [https://github.com/Heitorgmrc2004/robo.git](https://github.com/Heitorgmrc2004/robo.git)
cd robo
