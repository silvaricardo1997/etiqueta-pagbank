# Cortar Etiqueta PagBank (100×150 mm) – Web App (Streamlit)
**Modo: FIT em Lote (sem “recorte exato”)**

App para transformar etiquetas do **PagBank/Envio Fácil** geradas em **PDF A4** em páginas **100×150 mm (10×15 cm)** prontas para impressoras térmicas.  
Agora com **upload de vários arquivos** e saída em **um único PDF combinado** (multi‑página).

---

## ⚙️ Funcionalidades
- **Upload múltiplo** de PDFs A4 (uma ou mais etiquetas).
- Para **cada PDF**:
  - recorta a área informada em **mm** (coordenadas + margens extras) e
  - **redimensiona proporcionalmente** para **100×150 mm** (FIT, sem cortes).
- **Gera um PDF combinado** (multi‑página) com **todas** as etiquetas 100×150.
- Não há mais a opção de “recorte exato” (_crop_) — **apenas FIT**.

### Padrões (editáveis na barra lateral)
- `x_left_mm = 85.0`
- `y_top_mm = 34.0`
- `width_mm = 100.0`
- `height_mm = 150.0`
- `extra_top_mm = 14.0`
- `extra_right_mm = 18.6`
- `extra_left_mm = 0.0`
- `extra_bottom_mm = 0.0`
- **Página de saída:** `100 × 150 mm`

> Dica: “X da esquerda” é a medida em **mm** do **canto inferior esquerdo** da etiqueta até a borda **esquerda** da folha.  
> “Y do topo” é a medida do **topo da etiqueta** até a **borda superior** da folha.

---

## ▶️ Executar localmente
```bash
pip install streamlit PyPDF2
streamlit run app.py
```

**Arquivos** no repositório:
- `app.py` – código do app (Streamlit)
- `requirements.txt` – dependências
- `.streamlit/config.toml` – configs do servidor (ex.: limite de upload)

**Exemplo de `.streamlit/config.toml`:**
```toml
[server]
maxUploadSize = 200  # MB
```

---

## ☁️ Deploy gratuito

### Opção A — Streamlit Community Cloud (recomendado)
1. Crie um repositório **público** no GitHub com: `app.py`, `requirements.txt`, `.streamlit/config.toml`.
2. Acesse **https://share.streamlit.io → New app**.
3. Selecione seu **repo**, branch e `app.py` como **Main file path**.
4. Clique em **Deploy** → você recebe uma **URL pública**.

### Opção B — Hugging Face Spaces
1. Crie um Space (tipo **Streamlit**, **CPU Basic**).
2. Faça upload de `app.py`, `requirements.txt` e `.streamlit/config.toml` (ou conecte ao Git).
3. O Space fará o build e fornecerá uma **URL pública**.

---

## 🧭 Como usar
1. Abra o app e **envie um ou vários PDFs A4** com a etiqueta.
2. Ajuste os **parâmetros em mm** na barra lateral (os defaults acima já são os calibrados).
3. Selecione o **índice da página** (0 = primeira página) a processar em todos os arquivos.
4. Clique em **“Processar (somente FIT 100×150)”**.
5. Baixe os **arquivos individuais** ou o **PDF combinado** (“Baixar COMBINADO (100×150) – todos”).

---

## 🖨️ Dicas de impressão (Coibeu WKZ-80D ou similar)
- Mídia: **100 × 150 mm (10 × 15 cm)**.
- Escala: **Tamanho real / 100%** (desative “Ajustar à página”).\n- Desative margens automáticas do driver.\n\n---\n\n## 🔧 Solução de problemas\n- **ModuleNotFoundError (PyPDF2/streamlit)** → verifique se `requirements.txt` contém:\n  ```txt\n  streamlit>=1.30\n  PyPDF2>=3.0.0\n  ```\n- **Upload grande falha** → confira `maxUploadSize` em `.streamlit/config.toml` (ex.: `200 MB`).  \n- **Main file not found** no deploy → confirme `app.py` em **Main file path**.\n- **Corte desalinhado** → ajuste `extra_top_mm`, `extra_right_mm`, `extra_left_mm`, `extra_bottom_mm` em passos de 0,5–1,0 mm.\n\n---\n\nFeito com ❤️ para acelerar seu fluxo de impressão de etiquetas.\n
