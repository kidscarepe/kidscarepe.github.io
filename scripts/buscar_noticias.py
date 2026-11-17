#!/usr/bin/env python3
"""Robô de notícias automáticas da Kids Care.

Lê os feeds RSS de _data/fontes.yml e cria posts curtos em _posts/ com
título, resumo e link para a matéria original (sem copiar o texto completo).
Só usa a biblioteca padrão do Python.
"""
import hashlib, html, io, json, os, re, sys, unicodedata, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(RAIZ, "_posts")
# Fotos ilustrativas gratuitas (Unsplash) para notícias cuja matéria não tem foto
CAPAS = [
    "https://images.unsplash.com/photo-1587323655395-b1c77a12c89a?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1758598737516-ffd38ba74838?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1771765767087-ce71e4a7916a?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1537655780520-1e392ead81f2?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1758687126227-48c2fa04b653?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1758598738113-86c0f874c85a?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1643216755260-cb0bc30473c8?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1761208662734-fb46f1398551?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1600880291319-1a7499c191e8?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1646617747566-b7e784435a48?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1605627079912-97c3810a11a4?auto=format&fit=crop&w=1400&q=80",
    "https://images.unsplash.com/photo-1549068294-04a001ee0638?auto=format&fit=crop&w=1400&q=80",
]
FUSO = timezone(timedelta(hours=-3))  # Recife


def ler_config(caminho):
    """Leitor YAML mínimo para o formato de _data/fontes.yml."""
    cfg, lista, item = {}, None, None
    for linha in open(caminho, encoding="utf-8"):
        linha = re.sub(r"\s+#.*$", "", linha.rstrip("\n")) if not linha.strip().startswith("#") else ""
        if not linha.strip():
            continue
        m = re.match(r"^(\w+):\s*(.*)$", linha)
        if m:
            chave, valor = m.groups()
            if valor == "":
                lista = cfg.setdefault(chave, [])
            else:
                cfg[chave] = val(valor)
                lista = None
            continue
        m = re.match(r"^\s+-\s+(\w+):\s*(.*)$", linha)
        if m and lista is not None:
            item = {m.group(1): val(m.group(2))}
            lista.append(item)
            continue
        m = re.match(r"^\s+(\w+):\s*(.*)$", linha)
        if m and item is not None:
            item[m.group(1)] = val(m.group(2))
            continue
        m = re.match(r"^\s+-\s+(.*)$", linha)
        if m and lista is not None:
            lista.append(val(m.group(1)))
    return cfg


def val(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v in ("true", "false"):
        return v == "true"
    return int(v) if v.isdigit() else v


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def limpar(texto):
    texto = re.sub(r"<[^>]+>", " ", html.unescape(texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", norm(s)).strip("-")
    return s[:70].rstrip("-") or "noticia"


def yaml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PASTA_FOTOS = os.path.join(RAIZ, "assets", "img", "noticias", "auto")


def baixar(url, dados=None, cabecalhos=None):
    h = {"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"}
    h.update(cabecalhos or {})
    req = urllib.request.Request(url, data=dados, headers=h)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def resolver_google(url):
    """Converte o link do Google Notícias no link real da matéria."""
    m = re.search(r"news\.google\.com/(?:rss/)?articles/([^?/]+)", url)
    if not m:
        return url
    gid = m.group(1)
    try:
        pagina = baixar("https://news.google.com/articles/" + gid).decode("utf-8", "ignore")
        sg = re.search(r'data-n-a-sg="([^"]+)"', pagina).group(1)
        ts = re.search(r'data-n-a-ts="([^"]+)"', pagina).group(1)
        interno = ["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None, None, None, None, None, 0, 1],
                                  "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0], gid, int(ts), sg]
        freq = json.dumps([[["Fbv4je", json.dumps(interno), None, "generic"]]])
        resp = baixar("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                      urllib.parse.urlencode({"f.req": freq}).encode(),
                      {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}).decode("utf-8", "ignore")
        dados = json.loads(resp.split("\n\n")[1])
        real = json.loads(dados[0][2])[1]
        if real.startswith("http"):
            return real
    except Exception as e:
        print(f"[aviso] não consegui abrir o link do Google Notícias: {e}")
    return url


def meta_da_materia(url):
    """Lê a foto de capa (og:image) e o resumo (og:description) da matéria original."""
    try:
        pagina = baixar(url).decode("utf-8", "ignore")
    except Exception as e:
        print(f"[aviso] não consegui abrir a matéria {url}: {e}")
        return None, None

    def meta(*nomes):
        for n in nomes:
            for padrao in (r'<meta[^>]+(?:property|name)=["\']%s["\'][^>]*content=["\']([^"\']+)' % re.escape(n),
                           r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name)=["\']%s["\']' % re.escape(n)):
                m = re.search(padrao, pagina, re.I)
                if m:
                    return html.unescape(m.group(1)).strip()
        return None
    candidatas = []
    img = meta("og:image", "og:image:url", "og:image:secure_url", "twitter:image", "twitter:image:src")
    if img:
        candidatas.append(img)
    m = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]*href=["\']([^"\']+)', pagina, re.I)
    if m:
        candidatas.append(m.group(1))
    # Fotos dentro da própria matéria (img / amp-img), ignorando logos e ícones
    for m in re.finditer(r'<(?:img|amp-img)\b[^>]*?\s(?:data-src|data-lazy-src|src)=["\']([^"\']+\.(?:jpe?g|png|webp)(?:\?[^"\']*)?)["\']', pagina, re.I):
        src = m.group(1)
        if not re.search(r"logo|icon|avatar|sprite|banner|selo|brasao|bras%C3%A3o|whatsapp|facebook|instagram|twitter|youtube|pixel|placeholder", src, re.I):
            candidatas.append(src)
    vistos, unicas = set(), []
    for c in candidatas:
        c = urllib.parse.urljoin(url, html.unescape(c))
        if c not in vistos:
            vistos.add(c); unicas.append(c)
    desc = meta("og:description", "description", "twitter:description")
    if desc and desc.count(";") >= 3:  # descrição genérica de portal
        desc = None
    return unicas[:8], desc


def salvar_foto(url_img, fid):
    """Baixa a foto para o próprio site (evita imagens quebradas) e reduz o tamanho."""
    try:
        dados = baixar(url_img)
        if len(dados) < 2000:
            return None
        os.makedirs(PASTA_FOTOS, exist_ok=True)
        destino = os.path.join(PASTA_FOTOS, fid + ".jpg")
        try:
            from PIL import Image
            im = Image.open(io.BytesIO(dados)).convert("RGB")
            if im.width < 400 or im.height < 220 or im.width / im.height > 3:
                return None
            im.thumbnail((1200, 1200))
            im.save(destino, "JPEG", quality=80, optimize=True, progressive=True)
        except ImportError:
            open(destino, "wb").write(dados)
        return "/assets/img/noticias/auto/" + fid + ".jpg"
    except Exception as e:
        print(f"[aviso] não consegui baixar a foto {url_img}: {e}")
        return None


def foto_repetida(fid):
    """Mesma foto de outra notícia = mesma matéria publicada por outro veículo."""
    def soma(caminho):
        return hashlib.md5(open(caminho, "rb").read()).hexdigest()
    alvo = soma(os.path.join(PASTA_FOTOS, fid + ".jpg"))
    return any(soma(os.path.join(PASTA_FOTOS, n)) == alvo for n in os.listdir(PASTA_FOTOS) if n != fid + ".jpg")


def enriquecer(it):
    """Completa a notícia com link real, foto e resumo da matéria original."""
    it["link"] = resolver_google(it["link"])
    imgs, desc = meta_da_materia(it["link"])
    candidatas = ([it["imagem"]] if it.get("imagem") else []) + (imgs or [])
    for c in candidatas:
        it["foto_local"] = salvar_foto(c, it["id"])
        if it["foto_local"]:
            break
    if desc and (not it.get("resumo") or len(it["resumo"]) < 40):
        it["resumo"] = limpar(desc)
    return it


def itens(xml_bytes):
    raiz = ET.fromstring(xml_bytes)
    ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}
    for it in raiz.iter("item"):
        img = None
        for tag in ("{http://search.yahoo.com/mrss/}content", "{http://search.yahoo.com/mrss/}thumbnail", "enclosure"):
            el = it.find(tag)
            if el is not None and el.get("url") and (tag != "enclosure" or (el.get("type") or "").startswith("image")):
                img = el.get("url"); break
        if not img:
            m = re.search(r'<img[^>]+src="([^"]+)"', it.findtext("description") or "")
            img = m.group(1) if m else None
        fonte_el = it.find("source")
        yield {
            "titulo": limpar(it.findtext("title")),
            "link": (it.findtext("link") or "").strip(),
            "resumo": limpar(it.findtext("description")),
            "data": it.findtext("pubDate"),
            "imagem": img,
            "veiculo": limpar(fonte_el.text) if fonte_el is not None else None,
        }
    for it in raiz.iter("{http://www.w3.org/2005/Atom}entry"):
        link = it.find("atom:link", ns)
        yield {
            "titulo": limpar(it.findtext("atom:title", namespaces=ns)),
            "link": link.get("href") if link is not None else "",
            "resumo": limpar(it.findtext("atom:summary", namespaces=ns) or it.findtext("atom:content", namespaces=ns)),
            "data": it.findtext("atom:updated", namespaces=ns) or it.findtext("atom:published", namespaces=ns),
            "imagem": None, "veiculo": None,
        }


def data_de(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


PARADAS = set("a o as os de da do das dos e em no na nos nas para por com que um uma ao aos se sobre mais pela pelo".split())


def palavras(t):
    return {w for w in re.findall(r"[a-z0-9]+", norm(t)) if len(w) > 2 and w not in PARADAS}


def parecido(a, b):
    """Mesma notícia contada por veículos diferentes (títulos muito parecidos)."""
    A, B = palavras(a), palavras(b)
    if not A or not B:
        return False
    return len(A & B) / min(len(A), len(B)) >= 0.4


def titulos_existentes():
    out = []
    for nome in os.listdir(POSTS):
        m = re.search(r'^title:\s*"?(.*?)"?\s*$', open(os.path.join(POSTS, nome), encoding="utf-8").read(), re.M)
        if m:
            out.append(m.group(1))
    return out


def ids_existentes():
    ids = set()
    for nome in os.listdir(POSTS):
        with open(os.path.join(POSTS, nome), encoding="utf-8") as f:
            m = re.search(r"^fonte_id:\s*(\S+)", f.read(), re.M)
            if m:
                ids.add(m.group(1))
    return ids


def main():
    cfg = ler_config(os.environ.get("FONTES_CFG") or os.path.join(RAIZ, "_data", "fontes.yml"))
    if not cfg.get("ativo", True):
        print("Notícias automáticas desativadas em _data/fontes.yml"); return
    chaves = [norm(k) for k in cfg.get("palavras_chave", [])]
    locais = [norm(k) for k in cfg.get("locais", [])]
    tem = lambda lista, texto: any(re.search(r"\b" + re.escape(k) + r"\b", norm(texto)) for k in lista)
    limite = datetime.now(timezone.utc) - timedelta(days=int(cfg.get("dias_max", 3)))
    existentes = ids_existentes()
    vistos_titulo = {n[11:-3][:50] for n in os.listdir(POSTS) if n.endswith(".md")}
    candidatos = []
    titulos_ja = titulos_existentes()
    for fonte in cfg.get("fontes", []):
        try:
            dados = baixar(fonte["url"])
            lista = list(itens(dados))
        except Exception as e:
            print(f"[aviso] não consegui ler {fonte.get('nome')}: {e}"); continue
        print(f"{fonte.get('nome')}: {len(lista)} itens")
        for it in lista:
            if not it["titulo"] or not it["link"]:
                continue
            veiculo = it["veiculo"] or fonte["nome"]
            titulo = it["titulo"]
            if it["veiculo"] and titulo.endswith(" - " + it["veiculo"]):
                titulo = titulo[: -len(it["veiculo"]) - 3].strip()
            resumo = it["resumo"]
            if norm(resumo).startswith(norm(titulo)[:40]):  # Google Notícias repete o título
                resumo = ""
            d = data_de(it["data"]) or datetime.now(timezone.utc)
            if d < limite:
                continue
            if fonte.get("filtrar", True) and chaves and not tem(chaves, titulo + " " + resumo):
                continue
            fid = hashlib.sha1(it["link"].encode()).hexdigest()[:16]
            chave_titulo = slug(titulo)[:50]
            if fid in existentes or chave_titulo in vistos_titulo or any(parecido(titulo, t) for t in titulos_ja):
                continue
            titulos_ja.append(titulo)
            vistos_titulo.add(chave_titulo)
            candidatos.append(dict(it, titulo=titulo, resumo=resumo, veiculo=veiculo, data=d, id=fid))

    candidatos.sort(key=lambda x: x["data"], reverse=True)
    novos = candidatos[: int(cfg.get("max_por_dia", 3)) + 12]
    hoje = datetime.now(FUSO).strftime("%Y-%m-%d")
    ja_hoje = sum(1 for n in os.listdir(POSTS) if n.startswith(hoje) and "automatica: true" in open(os.path.join(POSTS, n), encoding="utf-8").read())
    limite_hoje = max(0, int(cfg.get("max_por_dia", 3)) - ja_hoje)
    print(f"Já publicadas hoje: {ja_hoje}. Ainda posso publicar: {limite_hoje}.")
    if limite_hoje == 0:
        novos = []
    publicados = 0
    for n, it in enumerate(novos):
        enriquecer(it)
        if locais and not tem(locais, it["titulo"] + " " + (it.get("resumo") or "")):
            print("Fora de Pernambuco, ignorada:", it["titulo"])
            if it.get("foto_local"):
                os.remove(os.path.join(PASTA_FOTOS, it["id"] + ".jpg"))
            continue
        if it.get("foto_local") and foto_repetida(it["id"]):
            print("Notícia repetida (mesma foto de outra já publicada):", it["titulo"])
            os.remove(os.path.join(PASTA_FOTOS, it["id"] + ".jpg"))
            continue
        d = it["data"].astimezone(FUSO)
        resumo = it["resumo"]
        if len(resumo) > 280:
            resumo = resumo[:280].rsplit(" ", 1)[0] + "…"
        descricao = resumo or f"Matéria publicada por {it['veiculo']}."
        capa = it.get("foto_local") or CAPAS[int(it["id"], 16) % len(CAPAS)]
        legenda = f"Foto: reprodução/{it['veiculo']}" if it.get("foto_local") else "Foto ilustrativa: Unsplash"
        nome = f"{d:%Y-%m-%d}-{slug(it['titulo'])}.md"
        corpo = f"""---
title: {yaml_str(it['titulo'])}
description: {yaml_str(descricao)}
date: {d:%Y-%m-%d %H:%M:%S %z}
image: {yaml_str(capa)}
legenda: {yaml_str(legenda)}
categories: [{yaml_str(cfg.get('categoria', 'Na mídia'))}]
author: {yaml_str(it['veiculo'])}
automatica: true
fonte: {yaml_str(it['veiculo'])}
link_fonte: {yaml_str(it['link'])}
fonte_id: {it['id']}
foto_tentativas: 1
---
{resumo}
"""
        with open(os.path.join(POSTS, nome), "w", encoding="utf-8") as f:
            f.write(corpo)
        print("Nova notícia:", nome)
        publicados += 1
        if publicados >= limite_hoje:
            break
    print(f"{publicados} notícia(s) nova(s).")
    completar_antigas()


def completar_antigas(limite=6):
    """Tenta colocar foto nas notícias automáticas antigas que ainda estão sem."""
    for nome in sorted(os.listdir(POSTS), reverse=True):
        if limite <= 0:
            break
        caminho = os.path.join(POSTS, nome)
        texto = open(caminho, encoding="utf-8").read()
        if "automatica: true" not in texto or ("/assets/img/auto/" not in texto and "images.unsplash.com" not in texto):
            continue
        tent = int((re.search(r"^foto_tentativas:\s*(\d+)", texto, re.M) or [0, "0"])[1])
        if tent >= 3:
            continue
        limite -= 1
        campo = lambda k: (re.search(r'^%s:\s*"?(.*?)"?\s*$' % k, texto, re.M) or [None, ""])[1]
        it = {"link": campo("link_fonte"), "id": campo("fonte_id"), "imagem": None, "resumo": ""}
        enriquecer(it)
        cab, corpo = texto.split("\n---\n", 1) if "\n---\n" in texto else (texto, "")
        cab = re.sub(r'^link_fonte:.*$', "link_fonte: " + yaml_str(it["link"]), cab, flags=re.M)
        if it.get("foto_local"):
            cab = re.sub(r'^image:.*$', "image: " + yaml_str(it["foto_local"]), cab, flags=re.M)
            veiculo = campo("fonte")
            cab = re.sub(r'^legenda:.*\n', "", cab, flags=re.M)
            cab = cab.replace("\ncategories:", "\nlegenda: " + yaml_str("Foto: reprodução/" + veiculo) + "\ncategories:", 1)
            print("Foto adicionada:", nome)
        if it.get("resumo") and campo("description").startswith("Matéria publicada por"):
            r = it["resumo"] if len(it["resumo"]) <= 280 else it["resumo"][:280].rsplit(" ", 1)[0] + "…"
            cab = re.sub(r'^description:.*$', "description: " + yaml_str(r), cab, flags=re.M)
            if not corpo.strip():
                corpo = r + "\n"
        cab = re.sub(r"^(foto_tentativas|foto_verificada):.*\n?", "", cab, flags=re.M).rstrip("\n")
        cab += "\nfoto_tentativas: %d" % (tent + 1)
        open(caminho, "w", encoding="utf-8").write(cab + "\n---\n" + corpo)


if __name__ == "__main__":
    sys.exit(main())
