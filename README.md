# Cortar Etiqueta PagBank (100×150 mm) – Web App (Streamlit)

App para recortar a etiqueta (dentro do retângulo tracejado) de PDFs A4 do PagBank/Envio Fácil,
gerando **(1) recorte exato** e **(2) versão ajustada para 100×150 mm** (fit proporcional).

## Executar localmente
```bash
pip install streamlit PyPDF2
streamlit run app.py
```

## Deploy gratuito — opções
### 1) Streamlit Community Cloud (recomendado, simples)
1. Crie um repositório no GitHub com estes arquivos: `app.py`, `requirements.txt`, `.streamlit/config.toml`.
2. Acesse https://share.streamlit.io (Streamlit Community Cloud) e clique em **New app**.
3. Escolha seu repositório, branch e `app.py` como **Main file path**. Clique em **Deploy**.
4. Você ganhará uma URL pública do app (gratuita).

> Dica: o arquivo `.streamlit/config.toml` já define `maxUploadSize = 200` (MB).

### 2) Hugging Face Spaces (também gratuito)
1. Crie uma conta em https://huggingface.co/ e clique em **New Space**.
2. Tipo: **Streamlit**. Selecione licença e **hardware CPU Basic** (gratuito).
3. Faça upload de `app.py`, `requirements.txt` e `.streamlit/config.toml` (ou conecte um repo Git).
4. O Space irá “Build & Run” automaticamente e fornecerá uma URL pública.

## Como usar
- Faça upload do PDF A4 com a etiqueta.
- Ajuste os campos em **mm** (padrões já prontos para 100×150 mm).
- Baixe o **_crop.pdf** (recorte exato) e o **_fit.pdf** (100×150).

## Observações
- Este app processa o PDF em memória e devolve o arquivo processado para download.
- Evite PDFs acima do limite de upload do host gratuito (200 MB configurado).

---
Crédito: gerado com ❤️ para facilitar a impressão em impressoras térmicas.
