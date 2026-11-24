import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

ARQUIVO_DADOS = "dados_treino.csv"
ARQUIVO_MODELO = "modelo_ia.pkl"

def treinar():
    if not os.path.exists(ARQUIVO_DADOS):
        print(f"Erro: O arquivo '{ARQUIVO_DADOS}' não foi encontrado na pasta atual.")
        return

    df = pd.read_csv(ARQUIVO_DADOS, encoding="utf-8")
    df = df.dropna(subset=["texto", "categoria"])

    modelo = make_pipeline(TfidfVectorizer(), MultinomialNB())
    modelo.fit(df["texto"], df["categoria"])

    joblib.dump(modelo, ARQUIVO_MODELO)
    print(f"Sucesso! Modelo treinado com {len(df)} exemplos e salvo em '{ARQUIVO_MODELO}'.")

if __name__ == "__main__":
    treinar()