import os, io, csv, time, base64, tempfile
import streamlit as st

st.set_page_config(page_title="Escola Sem Barreiras", page_icon="📚", layout="centered")

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
WHISPER = os.getenv("WHISPER_MODEL", "base")
try:
    KEY = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
except Exception:
    KEY = os.getenv("ANTHROPIC_API_KEY")

AUDIO = {"mp3", "wav", "m4a", "ogg", "flac"}
VIDEO = {"mp4", "mov", "mkv", "webm"}
MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
LEVELS = {
    "Muito simples (anos iniciais)": "bem simples, com frases curtas, para os anos iniciais do ensino fundamental",
    "Simples (ensino fundamental)": "simples e claro, para o ensino fundamental",
    "Intermediário (ensino médio)": "claro, com vocabulário próximo do original, para o ensino médio",
}
RULES = ("Preserve todos os conceitos, números, nomes e datas. Não invente informações. "
         "Não use markdown, asteriscos nem tabelas. Escreva em português do Brasil. Responda só com o resultado.")
FORMATS = {
    "simple": ("Texto simplificado",
        "Reescreva o texto abaixo em linguagem {lv}. Explique termos difíceis entre parênteses na primeira vez que aparecem. "
        "Use parágrafos curtos sem retirar conceitos essenciais. " + RULES + "\n\nTEXTO:\n{t}"),
    "bullets": ("Resumo em tópicos",
        "Resuma o texto abaixo em tópicos curtos, um por linha, começando com hífen. Linguagem {lv}. " + RULES + "\n\nTEXTO:\n{t}"),
    "glossary": ("Glossário de termos difíceis",
        "Liste os termos mais difíceis do texto abaixo, cada um em uma linha no formato 'termo: explicação curta'. Linguagem {lv}. " + RULES + "\n\nTEXTO:\n{t}"),
    "questions": ("Perguntas de compreensão",
        "Crie 5 perguntas curtas para checar a compreensão do texto abaixo, seguidas de uma linha 'Resposta esperada:' para o professor. Linguagem {lv}. " + RULES + "\n\nTEXTO:\n{t}"),
    "pictos": ("Apoio visual com emojis (comunicação alternativa)",
        "Para cada ideia principal do texto abaixo, escreva uma linha com 1 a 3 emojis seguidos de uma frase de até 6 palavras. " + RULES + "\n\nTEXTO:\n{t}"),
    "image": ("Descrição das imagens",
        "Descreva, para uma pessoa que não enxerga as imagens anexas, as informações visuais relevantes (figuras, gráficos, tabelas, mapas, "
        "setas, cores com significado). Para cada imagem: tipo, o que mostra e o que é importante entender. Linguagem {lv}. " + RULES),
}

# ---------- estilo ----------
S = st.session_state
for k, v in dict(text="", imgs=[], segs=[], media=None, out={}, orig={}, rev={}, log=[], mats=0, name="").items():
    S.setdefault(k, v)

with st.sidebar:
    st.header("Preferências")
    lv_name = st.selectbox("Nível da linguagem", list(LEVELS))
    size = st.slider("Tamanho do texto", 16, 28, 18)
    hc = st.toggle("Alto contraste")
    wide = st.toggle("Espaçamento amplo (leitura)")
LV = LEVELS[lv_name]

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Caveat+Brush&display=swap');
.stApp{{background-color:#f7fafd;background-image:linear-gradient(90deg,transparent 46px,#e8a5a5 46px,#e8a5a5 48px,transparent 48px),
repeating-linear-gradient(#f7fafd 0,#f7fafd 31px,#cfe0f1 31px,#cfe0f1 32px)}}
.block-container{{background:rgba(255,255,255,.9);border-radius:16px;padding:1.2rem 1.4rem 3rem!important;margin-top:1rem}}
.stMarkdown,.stMarkdown p,label,.stTextArea textarea,.stButton button,.stTabs button{{font-family:'Atkinson Hyperlegible',sans-serif!important;font-size:{size}px!important;
{'letter-spacing:.05em;word-spacing:.15em;line-height:1.9!important;' if wide else ''}}}
.board{{background:#1f4a3d;border:10px solid #8a5a33;border-radius:8px;padding:14px 18px;margin-bottom:10px;box-shadow:inset 0 0 30px rgba(0,0,0,.35),0 6px 0 #5d3b1f}}
.chalk{{font-family:'Caveat Brush',cursive;font-size:2.4rem;color:#f1f5ee;line-height:1.1}}
.board .sub{{color:#cfe3d6;font-family:'Atkinson Hyperlegible',sans-serif;font-size:1rem;margin-top:4px}}
.stTabs [role=tab]{{min-height:48px}}
button:focus-visible,textarea:focus-visible{{outline:3px solid #1d2a44!important;outline-offset:2px}}
{'.stApp{background-image:none!important;background-color:#fff!important}.block-container{background:#fff;border:3px solid #000}*{color:#000!important}.board *{color:#fff!important}' if hc else ''}
</style>
<div class="board"><div class="chalk">Escola Sem Barreiras</div>
<div class="sub">O mesmo conteúdo, no formato de que cada estudante precisa.</div></div>""", unsafe_allow_html=True)
st.caption("A IA apoia o trabalho pedagógico. Ela não substitui professores, profissionais do AEE, intérpretes de Libras ou revisores. Toda adaptação precisa de revisão humana.")

if not KEY:
    st.error("Chave da IA não encontrada. Defina ANTHROPIC_API_KEY em Secrets (veja o README).")
    st.stop()

# ---------- funções ----------
@st.cache_resource
def client():
    import anthropic
    return anthropic.Anthropic(api_key=KEY)

def ask(prompt, imgs=()):
    content = [{"type": "image", "source": {"type": "base64", "media_type": m, "data": base64.b64encode(b).decode()}}
               for b, m in list(imgs)[:6] if m in MIME.values() or m == "image/gif"]
    content.append({"type": "text", "text": prompt})
    r = client().messages.create(model=MODEL, max_tokens=4000, messages=[{"role": "user", "content": content}])
    return r.content[0].text.strip()

def read_pdf(b):
    import fitz
    d = fitz.open(stream=b, filetype="pdf")
    imgs = [(p.get_pixmap(dpi=100).tobytes("png"), "image/png") for p in list(d)[:6]]
    return "\n\n".join(p.get_text() for p in d).strip(), imgs

def read_pptx(b):
    from pptx import Presentation
    parts, imgs = [], []
    for i, s in enumerate(Presentation(io.BytesIO(b)).slides, 1):
        t = []
        for sh in s.shapes:
            if sh.has_text_frame: t.append(sh.text_frame.text)
            if sh.shape_type == 13 and len(imgs) < 6: imgs.append((sh.image.blob, sh.image.content_type))
        n = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        parts.append(f"Slide {i}:\n" + "\n".join(t) + (f"\nNotas do professor: {n}" if n else ""))
    return "\n\n".join(parts).strip(), imgs

@st.cache_resource
def whisper():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER, device="cpu", compute_type="int8")

def transcribe(b, ext):
    with tempfile.NamedTemporaryFile(suffix="." + ext, delete=False) as f:
        f.write(b); p = f.name
    try:
        segs, _ = whisper().transcribe(p, language="pt", vad_filter=True)
        return [(s.start, s.end, s.text.strip()) for s in segs]
    finally:
        os.remove(p)

def ts(t):
    h, r = divmod(int(t * 1000), 3600000); m, r = divmod(r, 60000); s, ms = divmod(r, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def srt(segs):
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(segs, 1))

def tts(text):
    from gtts import gTTS
    buf = io.BytesIO(); gTTS(text[:4500], lang="pt", tld="com.br").write_to_fp(buf); return buf.getvalue()

def reset():
    for k in ("text", "name"): S[k] = ""
    S.imgs, S.segs, S.media, S.out, S.orig, S.rev = [], [], None, {}, {}, {}
    for k in list(S.keys()):
        if k.startswith(("t_", "r_")): del S[k]

# ---------- interface ----------
tabs = st.tabs(["📥 Enviar", "✨ Adaptar", "✅ Revisar", "🎧 Acessar", "📊 Painel", "ℹ️ Sobre"])

with tabs[0]:
    up = st.file_uploader("PDF, foto, apresentação, vídeo ou áudio",
                          type=["pdf", "pptx", "png", "jpg", "jpeg", "webp"] + sorted(AUDIO | VIDEO))
    with st.expander("📷 Fotografar uma página (celular)"):
        cam = st.camera_input("Fotografe a página do livro ou caderno")
    if st.button("Ler o material", type="primary"):
        src = up or cam
        if not src:
            st.warning("Envie um arquivo ou tire uma foto.")
        else:
            reset()
            b = src.getvalue(); S.name = src.name
            ext = src.name.rsplit(".", 1)[-1].lower() if "." in src.name else "jpg"
            try:
                with st.spinner("Lendo o material… vídeos e áudios podem levar alguns minutos."):
                    if ext == "pdf": S.text, S.imgs = read_pdf(b)
                    elif ext == "pptx": S.text, S.imgs = read_pptx(b)
                    elif ext in MIME: S.imgs = [(b, MIME[ext])]
                    elif ext in AUDIO | VIDEO:
                        S.segs = transcribe(b, ext); S.text = " ".join(t for _, _, t in S.segs)
                        S.media = (b, "audio" if ext in AUDIO else "video")
                    if len(S.text) < 80 and S.imgs:
                        S.text = ask("Transcreva fielmente todo o texto visível nas imagens, na ordem de leitura, sem resumir nem corrigir. "
                                     "Marque [figura] onde houver figuras. Responda só com o texto.", S.imgs)
                S.mats += 1
                st.success("Material lido. Confira o texto abaixo antes de adaptar.")
            except Exception as e:
                st.error(f"Não foi possível ler o arquivo: {e}")
    if S.imgs:
        st.image([i for i, _ in S.imgs[:3]], width=160, caption=[f"Página/imagem {n}" for n in range(1, min(3, len(S.imgs)) + 1)])
    if S.media:
        (st.video if S.media[1] == "video" else st.audio)(S.media[0], **({"subtitles": {"Português": srt(S.segs).encode()}} if S.media[1] == "video" and S.segs else {}))
    if S.text or S.imgs:
        S.text = st.text_area("Texto do material (corrija se necessário)", S.text, height=220)

with tabs[1]:
    sel = st.multiselect("Quais adaptações gerar?", list(FORMATS), default=["simple"], format_func=lambda k: FORMATS[k][0])
    st.caption("Transcrição e legendas são geradas ao enviar vídeo ou áudio, na aba Enviar.")
    if st.button("Gerar adaptações", type="primary", disabled=not (S.text or S.imgs)):
        for k in sel:
            if k == "image" and not S.imgs: st.warning("Para descrever imagens, envie PDF, apresentação ou foto."); continue
            if k != "image" and not S.text.strip(): st.warning("Não há texto para adaptar."); continue
            t0 = time.time()
            try:
                with st.spinner(f"Gerando: {FORMATS[k][0]}…"):
                    S.out[k] = S.orig[k] = ask(FORMATS[k][1].format(lv=LV, t=S.text), S.imgs if k == "image" else ())
                S.rev[k] = False
                for p in ("t_", "r_"): S.pop(p + k, None)
                S.log.append({"formato": FORMATS[k][0], "segundos": round(time.time() - t0, 1)})
            except Exception as e:
                st.error(f"Erro ao gerar {FORMATS[k][0]}: {e}")
        st.success("Pronto. Vá para a aba Revisar.")

with tabs[2]:
    if not S.out: st.info("Gere uma adaptação primeiro.")
    for k in list(S.out):
        with st.expander(f"{FORMATS[k][0]} · gerado por IA", expanded=True):
            S.out[k] = st.text_area("Edite livremente", S.out[k], height=240, key="t_" + k)
            S.rev[k] = st.checkbox("Revisado por profissional responsável", key="r_" + k, value=S.rev.get(k, False))

with tabs[3]:
    opts = {"orig": "Texto original", **{k: FORMATS[k][0] for k in S.out}}
    k = st.selectbox("Texto para ouvir", list(opts), format_func=lambda x: opts[x])
    txt = S.text if k == "orig" else S.out.get(k, "")
    if k != "orig" and not S.rev.get(k): st.warning("Este conteúdo ainda não foi revisado por um profissional.")
    if st.button("🔊 Gerar narração em áudio", disabled=not txt):
        try:
            with st.spinner("Gerando áudio…"): S["mp3"] = tts(txt)
        except Exception as e:
            st.error(f"Falha ao gerar áudio: {e}")
    if S.get("mp3"):
        st.audio(S["mp3"], format="audio/mp3"); st.download_button("Baixar áudio (.mp3)", S["mp3"], "narracao.mp3")
    if S.segs:
        st.download_button("Baixar legendas (.srt)", srt(S.segs), "legendas.srt")
        st.download_button("Baixar transcrição (.txt)", S.text, "transcricao.txt")
    if S.out:
        pack = "\n\n".join(f"== {FORMATS[x][0]} ==\n{v}" + ("" if S.rev.get(x) else "\n[ATENÇÃO: gerado por IA, sem revisão humana]") for x, v in S.out.items())
        st.download_button("Baixar todas as adaptações (.txt)", pack, "adaptacoes.txt")

with tabs[4]:
    st.write("Indicadores medidos nesta sessão (nada é estimado).")
    ed = sum(1 for x in S.out if S.out[x].strip() != S.orig.get(x, "").strip())
    c = st.columns(2)
    c[0].metric("Materiais lidos", S.mats); c[1].metric("Adaptações geradas", len(S.log))
    c[0].metric("Revisadas", sum(bool(v) for v in S.rev.values())); c[1].metric("Editadas na revisão", ed)
    if S.log: st.metric("Tempo médio de geração (s)", round(sum(l["segundos"] for l in S.log) / len(S.log), 1))
    if S.log:
        o = io.StringIO(); w = csv.DictWriter(o, ["formato", "segundos"]); w.writeheader(); w.writerows(S.log)
        st.download_button("Baixar registro (.csv)", o.getvalue(), "registro.csv")

with tabs[5]:
    st.markdown("""**Automatizado:** leitura de texto (PDF, foto, slides), simplificação, descrição de imagens, transcrição e legendas, narração.

**Exige pessoas:** revisão do conteúdo; tradução para **Libras** (intérprete); conversão para **Braille** (profissional especializado); validação dos apoios visuais.

**Privacidade (LGPD):** os arquivos são enviados à API da Anthropic (texto e imagens) e o texto narrado ao Google (gTTS). Não envie dados pessoais de estudantes. Defina prazo de retenção e consentimento antes de um piloto.

**Transparência:** todo conteúdo gerado é marcado como IA e pode ser editado ou recusado pelo revisor.""")
