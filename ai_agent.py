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

NUMEROS_EXTENSO = {
    "um": "1", "dois": "2", "três": "3", "tres": "3", "quatro": "4", "cinco": "5",
    "seis": "6", "sete": "7", "oito": "8", "nove": "9", "dez": "10",
    "onze": "11", "doze": "12", "treze": "13", "quatorze": "14", "catorze": "14",
    "quinze": "15", "dezesseis": "16", "dezessete": "17", "dezoito": "18",
    "dezenove": "19", "vinte": "20", "primeiro": "1", "segundo": "2", "terceiro": "3",
    "quarto": "4", "quinto": "5", "sexto": "6", "sétimo": "7", "setimo": "7",
    "oitavo": "8", "nono": "9", "décimo": "10", "decimo": "10"
}

def extrair_numero_paragrafo(texto: str) -> str | None:
    t = texto.lower()
    # Verifica se tem dígito direto: "parágrafo 5", "paragrafo 12"
    m = re.search(r"par[aá]grafo\s+(\d+)", t)
    if m:
        return m.group(1)
    # Verifica por extenso: "parágrafo cinco", "parágrafo primeiro"
    for palavra, num in NUMEROS_EXTENSO.items():
        if re.search(rf"par[aá]grafo\s+{palavra}\b", t):
            return num
    return None

def localizar_paragrafo_no_texto(conteudo: str, num_p: str) -> str | None:
    linhas = [l.strip() for l in conteudo.splitlines() if l.strip()]
    inicio_idx = -1
    fim_idx = -1

    # Procura a linha que começa com o número do parágrafo, inclusive parágrafos duplos (ex: "5.", "4-5.", "5-6.")
    padrao_inicio = re.compile(rf"^(?:{num_p}(?:-\d+)?|\d+-{num_p})[\.\s]")

    for i, linha in enumerate(linhas):
        if padrao_inicio.match(linha):
            inicio_idx = i
            break

    if inicio_idx == -1:
        return None

    # Procura onde começa o próximo parágrafo para delimitar o fim
    padrao_proximo = re.compile(r"^\d+(?:-\d+)?[\.\s]")
    for j in range(inicio_idx + 1, len(linhas)):
        if padrao_proximo.match(linhas[j]):
            fim_idx = j
            break

    trecho = " ".join(linhas[inicio_idx:fim_idx] if fim_idx != -1 else linhas[inicio_idx:inicio_idx + 8])
    return trecho.strip()

LIVROS_BIBLIA = [
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

        # 3. Estudo de A Sentinela (artigo inteiro ou parágrafo específico)
        if "sentinela" in cmd or "parágrafo" in cmd or "paragrafo" in cmd:
            conteudo = await self.browser.obter_reuniao_semana_jw(tipo="sentinela")
            
            # Se o usuário pediu parágrafo específico (ex: "Ler parágrafo 5 de A Sentinela" ou "Ler parágrafo 2")
            num_p = extrair_numero_paragrafo(cmd)
            if num_p:
                trecho = localizar_paragrafo_no_texto(conteudo, num_p)
                if trecho:
                    return self._formatar_para_voz(f"Parágrafo {num_p} de A Sentinela: {trecho}")
                elif self._obter_groq():
                    resp_groq = self._consultar_groq(f"Leia exatamente o parágrafo {num_p} e a sua pergunta deste estudo de A Sentinela:\n{conteudo}")
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
