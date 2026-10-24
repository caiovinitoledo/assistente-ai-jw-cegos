import os
import re
from groq import Groq
from browser_service import BrowserService

SYSTEM_PROMPT = """
Você é um assistente de voz acessível e acolhedor projetado para pessoas cegas.
Regras estritas:
1. Suas respostas serão lidas em voz alta por um sintetizador de voz (TTS).
2. NUNCA use formatação Markdown como asteriscos (**), hashtags (#), sinais de igual (===), travessões ou links.
3. Responda de forma clara, natural, direta e em português do Brasil.
4. Quando receber conteúdo de reuniões, Bíblia ou publicações do jw.org, organize a leitura de forma agradável e fiel.
"""

LIVROS_BIBLIA = [
    "gênesis", "genesis", "êxodo", "exodo", "levítico", "levitico", "números", "numeros",
    "deuteronômio", "deuteronomio", "josué", "josue", "juízes", "juizes", "rute",
    "samuel", "reis", "crônicas", "cronicas", "esdras", "neemias", "ester", "jó", "jo",
    "salmos", "salmo", "provérbios", "proverbios", "eclesiastes", "cântico de salomão",
    "isaías", "isaias", "jeremias", "lamentações", "lamentacoes", "ezequiel", "daniel",
    "oseias", "oséias", "joel", "amós", "amos", "obadias", "jonas", "miqueias", "miquéias",
    "naum", "habacuque", "sofonias", "ageu", "zacarias", "malaquias",
    "mateus", "marcos", "lucas", "joão", "joao", "atos", "romanos", "coríntios", "corintios",
    "gálatas", "galatas", "efésios", "efesios", "filipenses", "colossenses",
    "tessalonicenses", "timóteo", "timoteo", "tito", "filêmon", "filemon", "filemom",
    "hebreus", "tiago", "pedro", "judas", "apocalipse", "revelação",
]

class AssistenteAcessivelIA:
    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        self.model_name = model_name
        self.browser = BrowserService(headless=True)
        self._groq_client = None

    def _obter_groq(self):
        if self._groq_client is None:
            api_key = os.environ.get("GROQ_API_KEY", "").strip()
            if api_key:
                self._groq_client = Groq(api_key=api_key)
        return self._groq_client

    def _formatar_para_voz(self, texto: str) -> str:
        limpo = re.sub(r"[=*#_~`>|]+", " ", texto)
        limpo = re.sub(r"\s+", " ", limpo)
        return limpo.strip()

    def _extrair_referencia_biblica(self, comando: str) -> str | None:
        cmd = comando.lower()
        cmd_norm = re.sub(r"\b(capítulo|capitulo)\s*(\d+)\s*(versículo|versiculo|verso|versículos|versiculos)\s*(\d+)", r"\2:\4", cmd)
        cmd_norm = re.sub(r"\b(capítulo|capitulo)\s*(\d+)", r"\2", cmd_norm)
        cmd_norm = re.sub(r"\b(versículo|versiculo|verso)\s*(\d+)", r":\2", cmd_norm)
        cmd_norm = re.sub(r"(\d+)\s*[:\s]\s*(\d+)\s+e\s+(\d+)", r"\1:\2-\3", cmd_norm)
        cmd_norm = re.sub(r"(\d+)\s*[:\s]\s*(\d+)\s+(?:a|ao|até|ate)\s+(\d+)", r"\1:\2-\3", cmd_norm)
        cmd_norm = re.sub(r"(\b\d{1,3})\s+(\d{1,3}\b)", r"\1:\2", cmd_norm)
        cmd_norm = re.sub(r"\b(primeiro|primeira)\s+", "1 ", cmd_norm)
        cmd_norm = re.sub(r"\b(segundo|segunda)\s+", "2 ", cmd_norm)
        cmd_norm = re.sub(r"\b(terceiro|terceira)\s+", "3 ", cmd_norm)

        for livro in LIVROS_BIBLIA:
            padrao = rf"((?:[123]\s+)?{livro}\s+\d+(?::\d+(?:-\d+)?)?)"
            match = re.search(padrao, cmd_norm)
            if match:
                return match.group(1).strip()
        return None

    def _consultar_groq(self, prompt_usuario: str, contexto: str = "") -> str | None:
        client = self._obter_groq()
        if not client:
            return None
        try:
            mensagens = [{"role": "system", "content": SYSTEM_PROMPT}]
            if contexto:
                mensagens.append({
                    "role": "user",
                    "content": f"Conteúdo original do site jw.org:\n{contexto[:6000]}\n\nPedido do usuário: {prompt_usuario}"
                })
            else:
                mensagens.append({"role": "user", "content": prompt_usuario})

            chat_completion = client.chat.completions.create(
                messages=mensagens,
                model=self.model_name,
                temperature=0.3,
                max_tokens=1024,
            )
            return self._formatar_para_voz(chat_completion.choices[0].message.content)
        except Exception:
            return None

    async def processar_comando(self, comando_usuario: str) -> str:
        cmd = re.sub(r"^(ok\s+|ei\s+|olá\s+|ola\s+)?assistente[,:\s]*", "", comando_usuario.lower().strip())

        # 1. Leitura de texto da Bíblia
        ref_biblica = self._extrair_referencia_biblica(cmd)
        if ref_biblica:
            conteudo = await self.browser.ler_texto_biblico_jw(ref_biblica)
            linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 1]
            leitura = ". ".join(linhas[:35])
            return self._formatar_para_voz(f"Leitura bíblica no J W ponto org, {ref_biblica}: {leitura}")

        # 2. Texto Diário
        if any(p in cmd for p in ["texto diário", "texto diario", "texto de hoje", "examine as escrituras"]):
            conteudo = await self.browser.obter_texto_diario_jw()
            linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas[:35])
            return self._formatar_para_voz(f"Texto diário de hoje no J W ponto org: {leitura}")

        # 3. Estudo de A Sentinela
        if "sentinela" in cmd:
            conteudo = await self.browser.obter_reuniao_semana_jw(tipo="sentinela")
            
            # Se o usuário pediu parágrafo específico (ex: "Ler parágrafo 5 de A Sentinela")
            match_paragrafo = re.search(r"par[aá]grafo\s+(\d+)", cmd)
            if match_paragrafo:
                num_p = match_paragrafo.group(1)
                # Tenta localizar o início do parágrafo desejado
                padrao_p = rf"(?:^|\.\s*)({num_p}\.\s+.*?)(?=(?:\.\s*\d+\.\s+)|$)"
                match_trecho = re.search(padrao_p, conteudo, re.DOTALL)
                if match_trecho:
                    return self._formatar_para_voz(f"Parágrafo {num_p} de A Sentinela: {match_trecho.group(1).strip()}")
                elif self._obter_groq():
                    resp_groq = self._consultar_groq(f"Localize e leia apenas o parágrafo {num_p} e a pergunta dele deste artigo de A Sentinela:\n{conteudo}")
                    if resp_groq:
                        return resp_groq

            if any(p in cmd for p in ["resumo", "recapitulação", "recapitulacao", "objetivo"]):
                resp_ia = self._consultar_groq(comando_usuario, conteudo)
                if resp_ia:
                    return resp_ia

            linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas)
            return self._formatar_para_voz(f"Estudo de A Sentinela desta semana no J W ponto org: {leitura}")

        # 4. Apostila Vida e Ministério / Reunião da Semana
        if any(p in cmd for p in ["reunião", "reuniao", "vida e ministério", "vida e ministerio", "apostila", "tesouros"]):
            tipo = "vida_e_ministerio" if ("vida" in cmd or "apostila" in cmd or "tesouros" in cmd) else "completa"
            conteudo = await self.browser.obter_reuniao_semana_jw(tipo=tipo)
            linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas[:70])
            return self._formatar_para_voz(f"Programação da reunião desta semana no J W ponto org: {leitura}")

        # 5. Pesquisa no JW.ORG
        if any(p in cmd for p in ["pesquisar no jw", "buscar no jw", "procurar no jw", "pesquisar sobre", "no jw sobre"]):
            termo = re.sub(r".*(pesquisar no jw sobre|pesquisar no jw|buscar no jw|procurar no jw|no jw sobre|pesquisar sobre)\s*", "", cmd).strip()
            if termo:
                conteudo = await self.browser.pesquisar_assunto_jw(termo)
                linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 2]
                leitura = ". ".join(linhas[:35])
                return self._formatar_para_voz(f"Resultados no J W ponto org sobre {termo}: {leitura}")

        # 6. Perguntas gerais ou inteligência conversacional com Groq
        resp_groq = self._consultar_groq(comando_usuario)
        if resp_groq:
            return resp_groq

        return (
            f"Estou ouvindo. Você disse: {comando_usuario}. "
            "Pode pedir: Ler Salmos 83 18, Ler A Sentinela da semana, "
            "Ler a reunião da semana, ou Ler o texto diário."
        )
