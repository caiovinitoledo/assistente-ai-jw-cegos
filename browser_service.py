import urllib.parse
import re
import asyncio
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
        self._cache_versiculos = {}
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=14.0)
        return self._client

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
            "Edição impressa",
        )
        linhas = [
            linha.strip()
            for linha in texto.splitlines()
            if len(linha.strip()) > 1
            and linha.strip() not in ("+", "*", "jw.org", ".", "Consultar")
            and not any(f in linha for f in frases_ignorar)
        ]
        return "\n".join(linhas)

    def _limpar_capitulo_biblico(self, texto: str, ref_capitulo: str) -> str:
        """
        Remove títulos repetidos do buscador da Bíblia (ex: 'Jeremias 45', '"Jeremias 45"', '(Jeremias 45)', '45')
        para que a voz neural leia fluentemente apenas o texto sagrado.
        """
        linhas = [l.strip() for l in texto.splitlines() if l.strip()]
        linhas_limpas = []
        ref_norm = re.sub(r"\s+", " ", ref_capitulo).lower()

        for l in linhas:
            l_norm = re.sub(r'["\(\)]', '', l).strip().lower()
            # Ignora repetições do cabeçalho da pesquisa
            if l_norm == ref_norm:
                continue
            if re.match(r"^[0-9]+(?::[0-9]+(?:-[0-9]+)?)?$", l):
                continue
            if l.startswith("(") and l.endswith(")"):
                continue
            linhas_limpas.append(l)

        return "\n".join(linhas_limpas)

    async def ler_texto_biblico_jw(self, referencia_biblica: str) -> str:
        ref_chave = referencia_biblica.strip().lower()
        if ref_chave in self._cache_versiculos:
            return self._cache_versiculos[ref_chave]

        query = urllib.parse.quote(referencia_biblica.strip())
        url = f"https://wol.jw.org/pt/wol/l/r5/lp-t?q={query}"
        try:
            client = await self._get_client()
            resp = await client.get(url)
            texto = self._limpar_html(resp.text, "#regionMain")
            if not texto or len(texto) < 5:
                res = f"Não encontrei o texto bíblico {referencia_biblica} no jw.org."
            else:
                res = texto[:5000]
            self._cache_versiculos[ref_chave] = res
            return res
        except Exception as e:
            return f"Erro ao buscar o texto bíblico {referencia_biblica} no jw.org: {str(e)}"

    async def obter_texto_diario_jw(self) -> str:
        hoje = datetime.now()
        url = f"https://wol.jw.org/pt/wol/h/r5/lp-t/{hoje.year}/{hoje.month}/{hoje.day}"
        try:
            client = await self._get_client()
            resp = await client.get(url)
            texto = self._limpar_html(resp.text, "#regionMain")
            return texto
        except Exception as e:
            return f"Não foi possível carregar o texto diário de hoje no jw.org: {str(e)}"

    async def pesquisar_assunto_jw(self, termo: str) -> str:
        query = urllib.parse.quote(termo.strip())
        url = f"https://wol.jw.org/pt/wol/s/r5/lp-t?q={query}"
        try:
            client = await self._get_client()
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
            client = await self._get_client()
            resp = await client.get(url_reuniao)
            soup = BeautifulSoup(resp.text, "html.parser")
            links_docs = [a.get("href", "") for a in soup.select("#regionMain a") if "/wol/d/r5/lp-t/" in a.get("href", "")]

            partes_extraidas = []
            if len(links_docs) >= 1 and tipo in ("completa", "vida_e_ministerio", "estudo_livro"):
                url_vm = f"https://wol.jw.org{links_docs[0]}"
                resp_vm = await client.get(url_vm)
                soup_vm = BeautifulSoup(resp_vm.text, "html.parser")

                # Se o pedido for especificamente o Estudo Bíblico de Congregação (Livro)
                if tipo == "estudo_livro":
                    link_livro = ""
                    # Procura exatamente a seção "Estudo bíblico de congregação"
                    for el in soup_vm.find_all(["h2", "h3", "h4", "strong", "p"]):
                        txt_el = el.get_text().lower()
                        if "estudo bíblico de congregação" in txt_el or "estudo biblico de congregacao" in txt_el:
                            # A matéria do livro está no próximo link antes do próximo cântico
                            for a in el.find_all_next("a"):
                                href = a.get("href", "")
                                txt_a = a.get_text().strip().lower()
                                if "cântico" in txt_a or "cantico" in txt_a:
                                    break
                                if "/wol/pc/" in href or "/wol/d/" in href:
                                    link_livro = href
                                    break
                            if link_livro:
                                break

                    # Fallback de busca reversa caso a estrutura mude
                    if not link_livro:
                        for a in reversed(soup_vm.select("a")):
                            href = a.get("href", "")
                            txt_a = a.get_text().strip().lower()
                            if ("/wol/pc/" in href or "/wol/d/" in href) and any(k in txt_a for k in ["cap.", "lição", "licao", "seção"]):
                                link_livro = href
                                break

                    if link_livro:
                        url_cap_livro = f"https://wol.jw.org{link_livro}"
                        resp_livro = await client.get(url_cap_livro)
                        texto_livro = self._limpar_html(resp_livro.text, "#article")
                        return f"Estudo Bíblico de Congregação desta semana:\n{texto_livro}"

                texto_vm = self._limpar_html(resp_vm.text, "#article")
                partes_extraidas.append(f"Reunião Nossa Vida e Ministério Cristão desta semana:\n{texto_vm}")

            if len(links_docs) >= 2 and tipo in ("completa", "sentinela"):
                url_sent = f"https://wol.jw.org{links_docs[1]}"
                resp_sent = await client.get(url_sent)
                texto_sent = self._limpar_html(resp_sent.text, "#article")
                partes_extraidas.append(f"Estudo de A Sentinela desta semana:\n{texto_sent}")

            if partes_extraidas:
                return "\n\n".join(partes_extraidas)
            return self._limpar_html(resp.text, "#regionMain")
        except Exception as e:
            return f"Não foi possível carregar a reunião no jw.org no momento: {str(e)}"

    async def obter_leitura_semanal_capitulos_biblia(self) -> str:
        """
        Extrai os capítulos de leitura da Bíblia da semana no topo da reunião (ex: JEREMIAS 45-46)
        e busca o texto bíblico integral dos capítulos na Tradução do Novo Mundo de forma paralela e rápida.
        """
        hoje = datetime.now()
        ano, semana, _ = hoje.isocalendar()
        url_reuniao = f"https://wol.jw.org/pt/wol/meetings/r5/lp-t/{ano}/{semana}"

        try:
            client = await self._get_client()
            resp = await client.get(url_reuniao)
            soup = BeautifulSoup(resp.text, "html.parser")
            links_docs = [a.get("href", "") for a in soup.select("#regionMain a") if "/wol/d/r5/lp-t/" in a.get("href", "")]

            if not links_docs:
                return "Não encontrei a programação de reuniões desta semana."

            url_vm = f"https://wol.jw.org{links_docs[0]}"
            resp_vm = await client.get(url_vm)
            soup_vm = BeautifulSoup(resp_vm.text, "html.parser")

            # Procura o link do cabeçalho de capítulos (ex: 'JEREMIAS 45-46')
            ref_capitulos = ""
            for a in soup_vm.select("a"):
                if "/wol/bc/" in a.get("href", ""):
                    txt = a.get_text(strip=True)
                    if re.search(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]+\s+\d+(?:-\d+)?", txt):
                        ref_capitulos = txt
                        break

            if not ref_capitulos:
                m = re.search(r"([A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]{3,})\s+(\d+)(?:-(\d+))?", resp_vm.text)
                if m:
                    ref_capitulos = m.group(0).strip()

            if not ref_capitulos:
                ref_capitulos = "Leitura semanal"

            # Busca os capítulos em paralelo
            m_faixa = re.search(r"([a-zA-ZáéíóúâêôãõçÁÉÍÓÚÂÊÔÃÕÇ\s]+)\s+(\d+)(?:-(\d+))?", ref_capitulos)
            if m_faixa:
                livro = m_faixa.group(1).strip().title()
                cap_ini = int(m_faixa.group(2))
                cap_fim = int(m_faixa.group(3)) if m_faixa.group(3) else cap_ini

                # Limita a 3 capítulos para não exceder tamanho excessivo de áudio
                cap_max = min(cap_fim, cap_ini + 2)
                capitulos_para_ler = list(range(cap_ini, cap_max + 1))

                tarefas = [self.ler_texto_biblico_jw(f"{livro} {cap}") for cap in capitulos_para_ler]
                resultados = await asyncio.gather(*tarefas)

                textos_lidos = []
                for cap, txt_cap in zip(capitulos_para_ler, resultados):
                    txt_limpo = self._limpar_capitulo_biblico(txt_cap, f"{livro} {cap}")
                    textos_lidos.append(f"Capítulo {cap}:\n{txt_limpo}")

                leitura_final = "\n\n".join(textos_lidos)
                return f"Leitura bíblica desta semana, {ref_capitulos}:\n{leitura_final}"

            # Fallback
            texto_biblico = await self.ler_texto_biblico_jw(ref_capitulos)
            return f"Leitura bíblica desta semana, {ref_capitulos}:\n{texto_biblico}"
        except Exception as e:
            return f"Erro ao buscar a leitura semanal da Bíblia: {str(e)}"

    async def acessar_pagina_generica(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        try:
            client = await self._get_client()
            resp = await client.get(url)
            texto = self._limpar_html(resp.text)
            if len(texto) > 100:
                return texto[:5000]
        except Exception as e:
            return f"Não foi possível abrir o site {url}: {str(e)}"
        return "Conteúdo indisponível para leitura."
