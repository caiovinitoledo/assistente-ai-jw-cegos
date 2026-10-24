import urllib.parse
import httpx
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

class BrowserService:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _limpar_html(self, html_content: str, seletor_principal: str = "#article, #regionMain, main") -> str:
        soup = BeautifulSoup(html_content, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "footer"]):
            tag.decompose()
        for extra in soup.select(".groupFootnote"):
            extra.decompose()
        if seletor_principal == "#article":
            for extra in soup.select("#studyDiscover, .studyDiscover"):
                extra.decompose()

        area = soup.select_one(seletor_principal) or soup.select_one("#regionMain") or soup
        texto = area.get_text(separator="\n")
        frases_ignorar = (
            "Nenhum vídeo disponível",
            "Desculpe, ocorreu um erro ao carregar o vídeo",
            "Tradução do Novo Mundo da Bíblia Sagrada",
            "BIBLIOTECA ON-LINE",
            "da Torre de Vigia",
            "Bem-vindo!",
            "Esta é uma ferramenta de pesquisa",
            "Para baixar publicações, acesse",
            "Sua resposta",
        )
        linhas = [
            linha.strip()
            for linha in texto.splitlines()
            if len(linha.strip()) > 1
            and linha.strip() not in ("+", "*", "jw.org", ".", "Consultar")
            and not any(f in linha for f in frases_ignorar)
        ]
        return "\n".join(linhas)

    async def ler_texto_biblico_jw(self, referencia_biblica: str) -> str:
        query = urllib.parse.quote(referencia_biblica.strip())
        url = f"https://wol.jw.org/pt/wol/l/r5/lp-t?q={query}"
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                resp = await client.get(url)
                texto = self._limpar_html(resp.text, "#regionMain")
                if not texto or len(texto) < 5:
                    return f"Não encontrei o texto bíblico {referencia_biblica} no jw.org."
                return texto[:4000]
        except Exception as e:
            return f"Erro ao buscar o texto bíblico {referencia_biblica} no jw.org: {str(e)}"

    async def obter_texto_diario_jw(self) -> str:
        hoje = datetime.now()
        url = f"https://wol.jw.org/pt/wol/h/r5/lp-t/{hoje.year}/{hoje.month}/{hoje.day}"
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                resp = await client.get(url)
                texto = self._limpar_html(resp.text, "#regionMain")
                return texto[:4000]
        except Exception as e:
            return f"Não foi possível carregar o texto diário de hoje no jw.org: {str(e)}"

    async def pesquisar_assunto_jw(self, termo: str) -> str:
        query = urllib.parse.quote(termo.strip())
        url = f"https://wol.jw.org/pt/wol/s/r5/lp-t?q={query}"
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                resp = await client.get(url)
                texto = self._limpar_html(resp.text, "#regionMain")
                return texto[:4000]
        except Exception as e:
            return f"Não foi possível pesquisar sobre {termo} no jw.org: {str(e)}"

    async def obter_reuniao_semana_jw(self, tipo: str = "completa") -> str:
        hoje = datetime.now()
        ano, semana, _ = hoje.isocalendar()
        url_reuniao = f"https://wol.jw.org/pt/wol/meetings/r5/lp-t/{ano}/{semana}"
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
                resp = await client.get(url_reuniao)
                soup = BeautifulSoup(resp.text, "html.parser")
                links_docs = []
                for a in soup.select("#regionMain a"):
                    href = a.get("href", "")
                    if "/wol/d/r5/lp-t/" in href and href not in links_docs:
                        links_docs.append(href)

                partes_extraidas = []
                if len(links_docs) >= 1 and tipo in ("completa", "vida_e_ministerio"):
                    url_vm = f"https://wol.jw.org{links_docs[0]}"
                    resp_vm = await client.get(url_vm)
                    texto_vm = self._limpar_html(resp_vm.text, "#article")
                    partes_extraidas.append(f"Reunião Nossa Vida e Ministério Cristão desta semana:\n{texto_vm[:4500]}")

                if len(links_docs) >= 2 and tipo in ("completa", "sentinela"):
                    url_sent = f"https://wol.jw.org{links_docs[1]}"
                    resp_sent = await client.get(url_sent)
                    texto_sent = self._limpar_html(resp_sent.text, "#article")
                    partes_extraidas.append(f"Estudo de A Sentinela desta semana:\n{texto_sent[:5500]}")

                if partes_extraidas:
                    return "\n\n".join(partes_extraidas)
                return self._limpar_html(resp.text, "#regionMain")[:5000]
        except Exception as e:
            return f"Não foi possível carregar a reunião no jw.org no momento: {str(e)}"

    async def acessar_pagina_generica(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(url)
                texto = self._limpar_html(resp.text)
                if len(texto) > 100:
                    return texto[:5000]
        except Exception as e:
            return f"Não foi possível abrir o site {url}: {str(e)}"
        return "Conteúdo indisponível para leitura."
