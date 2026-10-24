import os
import re
import asyncio
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

ABREVIACOES_BIBLIA = {
    "gên.": "Gênesis", "gên": "Gênesis", "gen.": "Gênesis", "gen": "Gênesis", "gn.": "Gênesis", "gn": "Gênesis",
    "êx.": "Êxodo", "êx": "Êxodo", "ex.": "Êxodo", "ex": "Êxodo",
    "lev.": "Levítico", "lev": "Levítico", "lv.": "Levítico", "lv": "Levítico",
    "núm.": "Números", "núm": "Números", "num.": "Números", "num": "Números", "nm.": "Números", "nm": "Números",
    "deut.": "Deuteronômio", "deut": "Deuteronômio", "dt.": "Deuteronômio", "dt": "Deuteronômio",
    "jos.": "Josué", "jos": "Josué", "js.": "Josué", "js": "Josué",
    "juí.": "Juízes", "juí": "Juízes", "jui.": "Juízes", "jui": "Juízes", "jz.": "Juízes", "jz": "Juízes",
    "rut.": "Rute", "rt.": "Rute", "rute": "Rute",
    "1 sam.": "1 Samuel", "1 sam": "1 Samuel", "1 sm.": "1 Samuel", "1 sm": "1 Samuel",
    "2 sam.": "2 Samuel", "2 sam": "2 Samuel", "2 sm.": "2 Samuel", "2 sm": "2 Samuel",
    "1 reis": "1 Reis", "1 rs.": "1 Reis", "1 rs": "1 Reis",
    "2 reis": "2 Reis", "2 rs.": "2 Reis", "2 rs": "2 Reis",
    "1 crô.": "1 Crônicas", "1 crô": "1 Crônicas", "1 cro.": "1 Crônicas", "1 cro": "1 Crônicas", "1 cr.": "1 Crônicas", "1 cr": "1 Crônicas",
    "2 crô.": "2 Crônicas", "2 crô": "2 Crônicas", "2 cro.": "2 Crônicas", "2 cro": "2 Crônicas", "2 cr.": "2 Crônicas", "2 cr": "2 Crônicas",
    "esd.": "Esdras", "esd": "Esdras", "ed.": "Esdras", "ed": "Esdras",
    "neem.": "Neemias", "neem": "Neemias", "ne.": "Neemias", "ne": "Neemias",
    "est.": "Ester", "est": "Ester", "et.": "Ester", "et": "Ester",
    "jó": "Jó", "jo": "Jó",
    "sal.": "Salmos", "sal": "Salmos", "sl.": "Salmos", "sl": "Salmos", "salmo": "Salmos", "salmos": "Salmos",
    "pr.": "Provérbios", "pr": "Provérbios", "prov.": "Provérbios", "prov": "Provérbios", "pv.": "Provérbios", "pv": "Provérbios",
    "ecl.": "Eclesiastes", "ecl": "Eclesiastes", "ec.": "Eclesiastes", "ec": "Eclesiastes",
    "cânt.": "Cântico de Salomão", "cant.": "Cântico de Salomão", "ct.": "Cântico de Salomão", "ct": "Cântico de Salomão",
    "isa.": "Isaías", "isa": "Isaías", "is.": "Isaías", "is": "Isaías", "isaias": "Isaías", "isaías": "Isaías",
    "jer.": "Jeremias", "jer": "Jeremias", "jr.": "Jeremias", "jr": "Jeremias",
    "lam.": "Lamentações", "lam": "Lamentações", "lm.": "Lamentações", "lm": "Lamentações",
    "ezeq.": "Ezequiel", "ezeq": "Ezequiel", "ez.": "Ezequiel", "ez": "Ezequiel",
    "dan.": "Daniel", "dan": "Daniel", "dn.": "Daniel", "dn": "Daniel",
    "osé.": "Oseias", "osé": "Oseias", "ose.": "Oseias", "ose": "Oseias", "os.": "Oseias", "os": "Oseias",
    "joel": "Joel", "jl.": "Joel", "jl": "Joel",
    "amós": "Amós", "amos": "Amós", "am.": "Amós", "am": "Amós",
    "obad.": "Obadias", "obad": "Obadias", "ob.": "Obadias", "ob": "Obadias",
    "jon.": "Jonas", "jon": "Jonas", "jn.": "Jonas", "jn": "Jonas", "jonas": "Jonas",
    "miq.": "Miqueias", "miq": "Miqueias", "mq.": "Miqueias", "mq": "Miqueias",
    "naum": "Naum", "na.": "Naum", "na": "Naum",
    "hab.": "Habacuque", "hab": "Habacuque", "hc.": "Habacuque", "hc": "Habacuque",
    "sof.": "Sofonias", "sof": "Sofonias", "sf.": "Sofonias", "sf": "Sofonias",
    "ageu": "Ageu", "ag.": "Ageu", "ag": "Ageu",
    "zac.": "Zacarias", "zac": "Zacarias", "zc.": "Zacarias", "zc": "Zacarias",
    "mal.": "Malaquias", "mal": "Malaquias", "ml.": "Malaquias", "ml": "Malaquias",
    "mat.": "Mateus", "mat": "Mateus", "mt.": "Mateus", "mt": "Mateus", "mateus": "Mateus",
    "mar.": "Marcos", "mar": "Marcos", "mc.": "Marcos", "mc": "Marcos", "marcos": "Marcos",
    "luc.": "Lucas", "luc": "Lucas", "lc.": "Lucas", "lc": "Lucas", "lucas": "Lucas",
    "joão": "João", "joao": "João", "jo.": "João", "jo": "João",
    "atos": "Atos", "at.": "Atos", "at": "Atos",
    "rom.": "Romanos", "rom": "Romanos", "rm.": "Romanos", "rm": "Romanos",
    "1 cor.": "1 Coríntios", "1 cor": "1 Coríntios", "1 co.": "1 Coríntios", "1 co": "1 Coríntios",
    "2 cor.": "2 Coríntios", "2 cor": "2 Coríntios", "2 co.": "2 Coríntios", "2 co": "2 Coríntios",
    "gál.": "Gálatas", "gál": "Gálatas", "gal.": "Gálatas", "gal": "Gálatas", "gl.": "Gálatas", "gl": "Gálatas",
    "efés.": "Efésios", "efés": "Efésios", "efes.": "Efésios", "efes": "Efésios", "ef.": "Efésios", "ef": "Efésios",
    "fil.": "Filipenses", "fil": "Filipenses", "fp.": "Filipenses", "fp": "Filipenses",
    "col.": "Colossenses", "col": "Colossenses", "cl.": "Colossenses", "cl": "Colossenses",
    "1 tess.": "1 Tessalonicenses", "1 tess": "1 Tessalonicenses", "1 ts.": "1 Tessalonicenses", "1 ts": "1 Tessalonicenses",
    "2 tess.": "2 Tessalonicenses", "2 tess": "2 Tessalonicenses", "2 ts.": "2 Tessalonicenses", "2 ts": "2 Tessalonicenses",
    "1 tim.": "1 Timóteo", "1 tim": "1 Timóteo", "1 tm.": "1 Timóteo", "1 tm": "1 Timóteo",
    "2 tim.": "2 Timóteo", "2 tim": "2 Timóteo", "2 tm.": "2 Timóteo", "2 tm": "2 Timóteo",
    "tito": "Tito", "tt.": "Tito", "tt": "Tito",
    "filêm.": "Filêmon", "filêm": "Filêmon", "filem.": "Filêmon", "filem": "Filêmon", "flm.": "Filêmon", "flm": "Filêmon", "fm.": "Filêmon", "fm": "Filêmon",
    "heb.": "Hebreus", "heb": "Hebreus", "hb.": "Hebreus", "hb": "Hebreus",
    "tia.": "Tiago", "tia": "Tiago", "tg.": "Tiago", "tg": "Tiago",
    "1 ped.": "1 Pedro", "1 ped": "1 Pedro", "1 pe.": "1 Pedro", "1 pe": "1 Pedro",
    "2 ped.": "2 Pedro", "2 ped": "2 Pedro", "2 pe.": "2 Pedro", "2 pe": "2 Pedro",
    "1 joão": "1 João", "1 joao": "1 João", "1 jo.": "1 João", "1 jo": "1 João",
    "2 joão": "2 João", "2 joao": "2 João", "2 jo.": "2 João", "2 jo": "2 João",
    "3 joão": "3 João", "3 joao": "3 João", "3 jo.": "3 João", "3 jo": "3 João",
    "jud.": "Judas", "jud": "Judas", "jd.": "Judas", "jd": "Judas", "judas": "Judas",
    "apo.": "Apocalipse", "apo": "Apocalipse", "apoc.": "Apocalipse", "apoc": "Apocalipse", "ap.": "Apocalipse", "ap": "Apocalipse", "rev.": "Apocalipse", "rev": "Apocalipse"
}

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
    m = re.search(r"par[aá]grafo\s+(\d+)", t)
    if m:
        return m.group(1)
    for palavra, num in NUMEROS_EXTENSO.items():
        if re.search(rf"par[aá]grafo\s+{palavra}\b", t):
            return num
    return None

def localizar_paragrafo_no_texto(conteudo: str, num_p: str) -> str | None:
    linhas = [l.strip() for l in conteudo.splitlines() if l.strip()]
    inicio_idx = -1
    fim_idx = -1

    # 1. Tenta encontrar parágrafo numerado (ex: "5.", "4-5.", "5-6.")
    padrao_inicio = re.compile(rf"^(?:{num_p}(?:-\d+)?|\d+-{num_p})[\.\s]")
    for i, linha in enumerate(linhas):
        if padrao_inicio.match(linha):
            inicio_idx = i
            break

    if inicio_idx != -1:
        padrao_proximo = re.compile(r"^\d+(?:-\d+)?[\.\s]")
        for j in range(inicio_idx + 1, len(linhas)):
            if padrao_proximo.match(linhas[j]):
                fim_idx = j
                break
        trecho = " ".join(linhas[inicio_idx:fim_idx] if fim_idx != -1 else linhas[inicio_idx:inicio_idx + 8])
        return trecho.strip()

    # 2. Se o texto não for numerado (ex: Estudo de Livro / Lições), divide por parágrafos longos
    try:
        idx_alvo = int(num_p) - 1
        paragrafos_corpo = [l for l in linhas if len(l) > 60 and not l.startswith("CÂNTICO") and not l.startswith("OBJETIVO")]
        if 0 <= idx_alvo < len(paragrafos_corpo):
            return paragrafos_corpo[idx_alvo]
    except Exception:
        pass

    return None

async def expandir_citacoes_biblicas_no_paragrafo(texto: str, browser: BrowserService) -> str:
    """
    Localiza todas as citações da Bíblia (ex: 'Pr. 27:11', 'Jer. 45:3', 'Is. 41:10', 'Deut. 31:23', 'Jos. 1:7'),
    busca os versículos em paralelo e substitui pela regra exata pedida:
    '[Livro Cap:Vers]. Lendo [Livro Cap:Vers]: [versículo completo]. Retornando ao parágrafo.'
    """
    padrao = re.compile(
        r"\(?\s*([123]\s+[a-zA-Záéíóúâêôãõç\.]+|[a-zA-Záéíóúâêôãõç\.]+)\s+(\d+(?::\d+(?:[-,]\s*\d+)?)?)\s*\)?",
        re.IGNORECASE
    )

    matches = list(padrao.finditer(texto))
    if not matches:
        return texto

    tarefas_busca = []
    itens_validos = []

    for m in matches:
        abreviacao_bruta = m.group(1).lower().strip()
        cap_vers = m.group(2).strip()
        livro_extenso = ABREVIACOES_BIBLIA.get(abreviacao_bruta) or ABREVIACOES_BIBLIA.get(abreviacao_bruta.rstrip("."))

        if livro_extenso:
            ref_completa = f"{livro_extenso} {cap_vers}"
            tarefas_busca.append(browser.ler_texto_biblico_jw(ref_completa))
            itens_validos.append((m, ref_completa))

    if not tarefas_busca:
        return texto

    # Busca todos os versículos citados no parágrafo em paralelo
    resultados_versiculos = await asyncio.gather(*tarefas_busca, return_exceptions=True)

    partes = []
    ultimo_fim = 0

    for (m, ref_completa), conteudo_v in zip(itens_validos, resultados_versiculos):
        versiculo_limpo = ""
        if isinstance(conteudo_v, str) and not conteudo_v.startswith("Erro") and not conteudo_v.startswith("Não encontrei"):
            linhas_v = [
                l.strip()
                for l in conteudo_v.splitlines()
                if len(l.strip()) > 1
                and not l.lower().startswith(ref_completa.lower())
                and not l.isdigit()
                and not l.startswith("(")
                and not l.startswith('"')
            ]
            versiculo_limpo = " ".join(linhas_v[:3]).strip()

        partes.append(texto[ultimo_fim:m.start()])
        if versiculo_limpo:
            partes.append(f" {ref_completa}. Lendo {ref_completa}: {versiculo_limpo}. Retornando ao parágrafo. ")
        else:
            partes.append(f" {ref_completa}. Lendo {ref_completa}. Retornando ao parágrafo. ")
        ultimo_fim = m.end()

    partes.append(texto[ultimo_fim:])
    return "".join(partes)

LIVROS_BIBLIA = [
    "gênesis", "genesis", "êxodo", "exodo", "levítico", "levitico", "números", "numeros",
    "deuteronômio", "deuteronomio", "josué", "josue", "juízes", "juizes", "rute",
    "samuel", "reis", "crônicas", "cronicas", "esdras", "neemias", "ester", "jó", "jo",
    "salmos", "salmo", "provérbios", "proverbios", "eclesiastes", "cântico de salomão", "cantico de salomao",
    "isaías", "isaias", "jeremias", "lamentações", "lamentacoes", "ezequiel", "daniel",
    "oseias", "oséias", "joel", "amós", "amos", "obadias", "jonas", "miqueias", "miquéias",
    "naum", "habacuque", "sofonias", "ageu", "zacarias", "malaquias",
    "mateus", "marcos", "lucas", "joão", "joao", "atos", "romanos", "coríntios", "corintios",
    "gálatas", "galatas", "efésios", "efesios", "filipenses", "colossenses",
    "tessalonicenses", "timóteo", "timoteo", "tito", "filêmon", "filemon", "filemom",
    "hebreus", "tiago", "pedro", "judas", "apocalipse", "revelação", "revelacao"
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

        # 1. Leitura dos Capítulos da Bíblia da semana (no início da programação da reunião semanal, ex: JEREMIAS 45 a 46)
        if any(p in cmd for p in [
            "leitura da bíblia dessa semana", "leitura da biblia dessa semana",
            "leitura da bíblia da semana", "leitura da biblia da semana",
            "leitura bíblica da semana", "leitura biblica da semana",
            "leitura bíblica dessa semana", "leitura biblica dessa semana",
            "leitura semanal da bíblia", "leitura semanal da biblia",
            "parte da bíblia dessa semana", "parte da biblia dessa semana",
            "parte da bíblia da semana", "parte da biblia da semana",
            "capítulos da bíblia", "capitulos da biblia",
            "capítulos da semana", "capitulos da semana",
            "bíblia dessa semana", "biblia dessa semana",
            "bíblia da semana", "biblia da semana"
        ]):
            conteudo = await self.browser.obter_leitura_semanal_capitulos_biblia()
            return self._formatar_para_voz(conteudo)

        # 2. Estudo Bíblico de Congregação (Livro da reunião de meio de semana, acessa o livro completo e expande citações)
        if any(p in cmd for p in [
            "estudo bíblico dessa semana", "estudo biblico dessa semana",
            "estudo bíblico da semana", "estudo biblico da semana",
            "estudo bíblico de congregação", "estudo biblico de congregacao",
            "estudo bíblico", "estudo biblico",
            "estudo de livro", "estudo do livro",
            "livro da semana", "livro dessa semana"
        ]):
            conteudo = await self.browser.obter_reuniao_semana_jw(tipo="estudo_livro")
            num_p = extrair_numero_paragrafo(cmd)
            if num_p:
                trecho = localizar_paragrafo_no_texto(conteudo, num_p)
                if trecho:
                    trecho_expandido = await expandir_citacoes_biblicas_no_paragrafo(trecho, self.browser)
                    return self._formatar_para_voz(f"Parágrafo {num_p} do Estudo Bíblico de Congregação: {trecho_expandido}")

            conteudo_expandido = await expandir_citacoes_biblicas_no_paragrafo(conteudo, self.browser)
            linhas = [l.strip() for l in conteudo_expandido.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas)
            return self._formatar_para_voz(leitura)

        # 3. Leitura de texto específico da Bíblia (ex: "Ler Isaías 41 10", "Salmos 83 18")
        ref_biblica = self._extrair_referencia_biblica(cmd)
        if ref_biblica:
            conteudo = await self.browser.ler_texto_biblico_jw(ref_biblica)
            linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 1]
            leitura = ". ".join(linhas[:35])
            return self._formatar_para_voz(f"Leitura bíblica no J W ponto org, {ref_biblica}: {leitura}")

        # 4. Texto Diário (com expansão de textos citados no comentário)
        if any(p in cmd for p in ["texto diário", "texto diario", "texto de hoje", "examine as escrituras"]):
            conteudo = await self.browser.obter_texto_diario_jw()
            conteudo_expandido = await expandir_citacoes_biblicas_no_paragrafo(conteudo, self.browser)
            linhas = [l.strip() for l in conteudo_expandido.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas)
            return self._formatar_para_voz(f"Texto diário de hoje no J W ponto org: {leitura}")

        # 5. Estudo de A Sentinela (artigo inteiro ou parágrafo específico com expansão de textos)
        if "sentinela" in cmd or ("parágrafo" in cmd and "bíblico" not in cmd and "livro" not in cmd) or ("paragrafo" in cmd and "biblico" not in cmd and "livro" not in cmd):
            conteudo = await self.browser.obter_reuniao_semana_jw(tipo="sentinela")
            
            num_p = extrair_numero_paragrafo(cmd)
            if num_p:
                trecho = localizar_paragrafo_no_texto(conteudo, num_p)
                if trecho:
                    trecho_expandido = await expandir_citacoes_biblicas_no_paragrafo(trecho, self.browser)
                    return self._formatar_para_voz(f"Parágrafo {num_p} de A Sentinela: {trecho_expandido}")
                elif self._obter_groq():
                    resp_groq = self._consultar_groq(f"Leia exatamente o parágrafo {num_p} e a sua pergunta deste estudo de A Sentinela:\n{conteudo}")
                    if resp_groq:
                        return resp_groq

            if any(p in cmd for p in ["resumo", "recapitulação", "recapitulacao", "objetivo"]):
                resp_ia = self._consultar_groq(comando_usuario, conteudo)
                if resp_ia:
                    return resp_ia

            conteudo_expandido = await expandir_citacoes_biblicas_no_paragrafo(conteudo, self.browser)
            linhas = [l.strip() for l in conteudo_expandido.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas)
            return self._formatar_para_voz(f"Estudo de A Sentinela desta semana no J W ponto org: {leitura}")

        # 6. Reunião Completa ou Apostila Vida e Ministério
        if any(p in cmd for p in ["reunião", "reuniao", "vida e ministério", "vida e ministerio", "apostila", "tesouros"]):
            tipo = "vida_e_ministerio" if ("vida" in cmd or "apostila" in cmd or "tesouros" in cmd) else "completa"
            conteudo = await self.browser.obter_reuniao_semana_jw(tipo=tipo)
            linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 2]
            leitura = ". ".join(linhas[:70])
            return self._formatar_para_voz(f"Programação da reunião desta semana no J W ponto org: {leitura}")

        # 7. Pesquisa no JW.ORG
        if any(p in cmd for p in ["pesquisar no jw", "buscar no jw", "procurar no jw", "pesquisar sobre", "no jw sobre"]):
            termo = re.sub(r".*(pesquisar no jw sobre|pesquisar no jw|buscar no jw|procurar no jw|no jw sobre|pesquisar sobre)\s*", "", cmd).strip()
            if termo:
                conteudo = await self.browser.pesquisar_assunto_jw(termo)
                linhas = [l.strip() for l in conteudo.splitlines() if len(l.strip()) > 2]
                leitura = ". ".join(linhas[:35])
                return self._formatar_para_voz(f"Resultados no J W ponto org sobre {termo}: {leitura}")

        # 8. Perguntas gerais com Groq
        resp_groq = self._consultar_groq(comando_usuario)
        if resp_groq:
            return resp_groq

        return (
            f"Estou ouvindo. Você disse: {comando_usuario}. "
            "Pode pedir: Ler a leitura da Bíblia dessa semana, "
            "Ler o estudo bíblico dessa semana, Ler A Sentinela da semana, "
            "ou Ler o texto diário."
        )
