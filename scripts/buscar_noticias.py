#!/usr/bin/env python3
"""Robô de notícias automáticas da Kids Care.

Lê os feeds RSS de _data/fontes.yml e cria posts curtos em _posts/ com
título, resumo e link para a matéria original (sem copiar o texto completo).
Só usa a biblioteca padrão do Python.
"""
import hashlib, html, os, re, sys, unicodedata, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(RAIZ, "_posts")
CAPAS = ["/assets/img/auto/auto-%d.jpg" % i for i in range(1, 7)]
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


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; blog-noticias-bot/1.0)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


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
    limite = datetime.now(timezone.utc) - timedelta(days=int(cfg.get("dias_max", 3)))
    existentes = ids_existentes()
    vistos_titulo = set()
    candidatos = []
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
            if fonte.get("filtrar", True) and not any(re.search(r"\b" + re.escape(k) + r"\b", norm(titulo + " " + resumo)) for k in chaves):
                continue
            fid = hashlib.sha1(it["link"].encode()).hexdigest()[:16]
            chave_titulo = slug(titulo)[:50]
            if fid in existentes or chave_titulo in vistos_titulo:
                continue
            vistos_titulo.add(chave_titulo)
            candidatos.append(dict(it, titulo=titulo, resumo=resumo, veiculo=veiculo, data=d, id=fid))

    candidatos.sort(key=lambda x: x["data"], reverse=True)
    novos = candidatos[: int(cfg.get("max_por_dia", 3))]
    for n, it in enumerate(novos):
        d = it["data"].astimezone(FUSO)
        resumo = it["resumo"]
        if len(resumo) > 280:
            resumo = resumo[:280].rsplit(" ", 1)[0] + "…"
        descricao = resumo or f"Matéria publicada por {it['veiculo']}."
        capa = it["imagem"] or CAPAS[int(it["id"], 16) % len(CAPAS)]
        nome = f"{d:%Y-%m-%d}-{slug(it['titulo'])}.md"
        corpo = f"""---
title: {yaml_str(it['titulo'])}
description: {yaml_str(descricao)}
date: {d:%Y-%m-%d %H:%M:%S %z}
image: {yaml_str(capa)}
categories: [{yaml_str(cfg.get('categoria', 'Na mídia'))}]
author: {yaml_str(it['veiculo'])}
automatica: true
fonte: {yaml_str(it['veiculo'])}
link_fonte: {yaml_str(it['link'])}
fonte_id: {it['id']}
---
{resumo}
"""
        with open(os.path.join(POSTS, nome), "w", encoding="utf-8") as f:
            f.write(corpo)
        print("Nova notícia:", nome)
    print(f"{len(novos)} notícia(s) nova(s).")


if __name__ == "__main__":
    sys.exit(main())
