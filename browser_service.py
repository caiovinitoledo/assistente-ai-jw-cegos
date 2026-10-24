import urllib.parse
import httpx
from playwright.async_api import async_playwright
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
    """
    Serviço completo para navegar no wol.jw.org (Reuniões, A Sentinela,
    Bíblia Tradução do Novo Mundo, Texto Diário, Pesquisa) e sites da web.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless

    def _limpar_html(self, html_content: str, seletor_principal: str = "#article, #regionMain, main") -> str:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove elementos ocultos ou secundários (cuidado: no WOL /wol/l/, os versículos ficam dentro de <nav>)
        for tag in soup(["script", "style", "noscript", "svg", "footer"]):
            tag.decompose()
        for extra in soup.select(".groupFootnote"):
            extra.decompose()
        # Só remove #studyDiscover se estivermos lendo um artigo principal (#article)
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
        """
        Busca um versículo ou capítulo da Bíblia diretamente na Tradução do Novo Mundo
        no domínio wol.jw.org (ex: 'Salmos 83:18', 'João 17:3', 'Apocalipse 21:3-4').
        """
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
        """
        Busca o Texto Diário de hoje (Examine as Escrituras Diariamente) no wol.jw.org.
        """
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
        """
        Pesquisa qualquer assunto ou publicação na Biblioteca On-line (wol.jw.org).
        """
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
        """
        Acessa a página de reuniões da semana atual no wol.jw.org,
        segue os links da Apostila Vida e Ministério e/ou do Estudo de A Sentinela.
        """
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
            return f"Não foi possível carregar a reunião no jw.org no momento. Detalhe: {str(e)}"

    async def acessar_pagina_generica(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=10.0) as client:
                resp = await client.get(url)
                texto = self._limpar_html(resp.text)
                if len(texto) > 100:
                    return texto[:5000]
        except Exception:
            pass

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                html = await page.content()
                await browser.close()
                return self._limpar_html(html)[:5000]
        except Exception as e:
            return f"Não foi possível abrir o site {url}. Detalhe: {str(e)}"
