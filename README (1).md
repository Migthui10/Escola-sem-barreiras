# Escola Sem Barreiras

Protótipo de hackathon (tema: IA Inclusiva). Recebe PDF, foto, apresentação (.pptx), vídeo e áudio e gera: texto simplificado, resumo em tópicos, glossário, perguntas de compreensão, apoio visual com emojis, descrição de imagens, transcrição, legendas (.srt) e narração em áudio. Tem etapa de revisão humana e painel de indicadores. Funciona no celular e no computador pelo navegador.

> A IA apoia o trabalho pedagógico e não substitui professores, profissionais do AEE, intérpretes de Libras ou revisores.

## Rodar no computador
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p .streamlit && cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite secrets.toml e coloque sua ANTHROPIC_API_KEY
streamlit run app.py
```
A primeira transcrição baixa o modelo Whisper (`base`). Para mais qualidade: `WHISPER_MODEL=small streamlit run app.py`.

## Publicar no GitHub
1. Crie uma conta em github.com e clique em **New repository**. Nome: `escola-sem-barreiras`. Deixe **Public** e clique em **Create repository**.
2. Pelo site: **Add file > Upload files**, arraste `app.py`, `requirements.txt`, `README.md`, `.gitignore` e a pasta `.streamlit` (somente `config.toml` e `secrets.toml.example`) e clique em **Commit changes**.
   Pelo terminal:
   ```bash
   git init && git add . && git commit -m "Primeira versão"
   git branch -M main
   git remote add origin https://github.com/SEU-USUARIO/escola-sem-barreiras.git
   git push -u origin main
   ```
3. **Nunca** suba o arquivo `secrets.toml` com a chave (o `.gitignore` já o bloqueia).

## Colocar no ar (link para a banca)
1. Acesse share.streamlit.io e entre com o GitHub.
2. **Create app**, escolha o repositório, branch `main`, arquivo `app.py`.
3. Em **Advanced settings**, escolha Python 3.11 e, em **Secrets**, cole: `ANTHROPIC_API_KEY = "sua-chave"`.
4. Clique em **Deploy**. O link funciona no celular.

## Roteiro de demonstração (3 min)
1. Envie um PDF didático de domínio público. 2. Mostre o texto lido. 3. Gere texto simplificado e descrição de imagem. 4. Edite algo e marque como revisado. 5. Gere a narração. 6. Envie um áudio curto e mostre a transcrição e as legendas. 7. Mostre o Painel.

## Limites conhecidos
Libras e Braille não são gerados. Vídeos longos demoram na transcrição. Confira sempre as adaptações. Valide os números do projeto no Inep e no IBGE.
