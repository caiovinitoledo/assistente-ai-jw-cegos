import os
import tempfile
import edge_tts
import speech_recognition as sr
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from ai_agent import AssistenteAcessivelIA

app = FastAPI(
    title="API Assistente de Voz Acessível",
    description="Backend com Groq + JW.ORG + Vozes Neurais Realistas para navegação acessível",
)

@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistente = AssistenteAcessivelIA()

VOZ_NEURAL_PADRAO = "pt-BR-FranciscaNeural"

class ComandoRequest(BaseModel):
    comando: str

class ComandoResponse(BaseModel):
    comando_reconhecido: str
    resposta_falada: str

class AudioRequest(BaseModel):
    texto: str

@app.get("/health")
async def health_check():
    return {"status": "online", "modelo": assistente.model_name}

@app.post("/falar-audio")
async def sintetizar_voz_neural(dados: AudioRequest):
    """
    Gera o áudio MP3 com voz neural humana via POST (sem limite de tamanho de URL).
    """
    texto = dados.texto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto vazio.")
    try:
        # Limita a 5000 caracteres por chamada para garantir resposta rápida
        comunicador = edge_tts.Communicate(texto[:5000], VOZ_NEURAL_PADRAO, rate="+5%")
        dados_audio = bytearray()
        async for chunk in comunicador.stream():
            if chunk["type"] == "audio":
                dados_audio.extend(chunk["data"])
        return Response(content=bytes(dados_audio), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/manifest.json")
async def pwa_manifest():
    return JSONResponse(
        {
            "name": "Assistente Acessível JW",
            "short_name": "Assistente",
            "description": "Navegador por comando de voz para pessoas cegas (JW.ORG e Internet)",
            "start_url": "/app?autostart=1",
            "display": "standalone",
            "background_color": "#000000",
            "theme_color": "#1A365D",
            "orientation": "portrait",
            "icons": [
                {
                    "src": "https://cdn-icons-png.flaticon.com/512/2593/2593635.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "any maskable",
                }
            ],
        }
    )

@app.get("/sw.js")
async def service_worker():
    js = """
    self.addEventListener('install', (e) => self.skipWaiting());
    self.addEventListener('activate', (e) => self.clients.claim());
    self.addEventListener('fetch', (e) => {});
    """
    return HTMLResponse(content=js, media_type="application/javascript")

@app.get("/app", response_class=HTMLResponse)
async def web_app_celular():
    return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <meta name="theme-color" content="#1A365D" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="Assistente Acessível" />
  <link rel="manifest" href="/manifest.json" />
  <title>Assistente Acessível</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
    body { background: #000; color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    .btn-voz {
      flex: 5; background: #1A365D; color: #fff; border: none; border-bottom: 5px solid #FFD700;
      display: flex; flex-direction: column; justify-content: center; align-items: center;
      padding: 24px; cursor: pointer; width: 100%;
    }
    .btn-voz.ouvindo { background: #9B2C2C; animation: pulsar 1.5s infinite; }
    .btn-voz.carregando { background: #744210; }
    @keyframes pulsar {
      0% { opacity: 1; }
      50% { opacity: 0.78; }
      100% { opacity: 1; }
    }
    .titulo { font-size: 28px; font-weight: bold; text-align: center; }
    .subtitulo { font-size: 19px; color: #FFD700; margin-top: 12px; text-align: center; }
    .area-leitura {
      flex: 5; background: #121212; padding: 22px; display: flex; flex-direction: column;
      cursor: pointer; overflow-y: auto;
    }
    .rotulo { color: #FFD700; font-size: 16px; font-weight: bold; margin-bottom: 12px; text-align: center; }
    .texto { font-size: 21px; line-height: 1.5; color: #fff; }
  </style>
</head>
<body>
  <button id="btnVoz" class="btn-voz" onclick="lidarComToque()">
    <div id="txtBotao" class="titulo">🎙️ TOQUE PARA FALAR</div>
    <div id="txtComando" class="subtitulo">Ex: "Ler Salmos 83 18", "Ler A Sentinela", "Ler a reunião"</div>
  </button>

  <div class="area-leitura" onclick="lidarComToque()">
    <div class="rotulo">🔊 1 TOQUE: PAUSAR | 2 TOQUES: CONTINUAR | 1 TOQUE EM PAUSA: NOVO COMANDO</div>
    <div id="txtResposta" class="texto">
      Toque na tela e diga o que deseja ouvir. Por exemplo: Ler Salmos 83 18, Ler A Sentinela da semana ou Ler o texto diário.
    </div>
  </div>

  <audio id="playerAudio" style="display:none;"></audio>

  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js');
    }

    async function manterTelaAtiva() {
      try {
        if ('wakeLock' in navigator) await navigator.wakeLock.request('screen');
      } catch (e) {}
    }
    manterTelaAtiva();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition = null;
    let processando = false;
    let audioAtual = document.getElementById('playerAudio');
    let blobUrlAtual = null;

    // Estados da Máquina de Áudio: 'ocioso', 'falando', 'pausado', 'ouvindo'
    let estadoAtual = 'ocioso';
    let timerCliqueDuplo = null;
    let ultimoTempoClique = 0;

    function tocarBip(freq = 660, duracao = 120) {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = freq;
        gain.gain.value = 0.15;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        setTimeout(() => { osc.stop(); ctx.close(); }, duracao);
      } catch (e) {}
    }

    function pararMicrofone() {
      if (recognition) {
        try { recognition.abort(); } catch (e) {}
      }
      const btn = document.getElementById('btnVoz');
      btn.classList.remove('ouvindo');
      btn.classList.remove('carregando');
    }

    function iniciarEscuta() {
      if (processando) return;
      if (audioAtual) {
        audioAtual.pause();
      }
      estadoAtual = 'ouvindo';

      if (!SpeechRecognition) {
        const manual = prompt("Digite seu pedido:");
        if (manual) processarComando(manual);
        return;
      }

      recognition = new SpeechRecognition();
      recognition.lang = 'pt-BR';
      recognition.continuous = false;
      recognition.interimResults = false;

      const btn = document.getElementById('btnVoz');
      const txt = document.getElementById('txtBotao');

      recognition.onstart = () => {
        tocarBip(740, 100);
        btn.classList.add('ouvindo');
        txt.innerText = "🔴 OUVINDO... PODE FALAR!";
      };

      recognition.onresult = (e) => {
        const texto = e.results[0][0].transcript;
        if (texto && texto.trim()) {
          tocarBip(520, 100);
          processarComando(texto.trim());
        }
      };

      recognition.onerror = () => {
        btn.classList.remove('ouvindo');
        txt.innerText = "🎙️ TOQUE PARA FALAR";
        estadoAtual = 'ocioso';
      };

      recognition.onend = () => {
        btn.classList.remove('ouvindo');
        if (estadoAtual === 'ouvindo') {
          txt.innerText = "🎙️ TOQUE PARA FALAR";
          estadoAtual = 'ocioso';
        }
      };

      try {
        recognition.start();
      } catch (e) {}
    }

    // Gerenciador de Toques Inteligente (Anti-Toque Acidental)
    function lidarComToque() {
      const agora = Date.now();
      const intervalo = agora - ultimoTempoClique;
      ultimoTempoClique = agora;

      // DETECÇÃO DE DUPLO TOQUE (intervalo menor que 350ms)
      if (intervalo < 350) {
        if (timerCliqueDuplo) {
          clearTimeout(timerCliqueDuplo);
          timerCliqueDuplo = null;
        }
        executarAcaoDuploToque();
        return;
      }

      // TOQUE ÚNICO COM DELAY PARA NÃO CONFLITAR COM DUPLO TOQUE
      timerCliqueDuplo = setTimeout(() => {
        executarAcaoToqueUnico();
        timerCliqueDuplo = null;
      }, 300);
    }

    function executarAcaoToqueUnico() {
      if (estadoAtual === 'falando') {
        // Pausa a leitura sem perder o ponto onde estava!
        audioAtual.pause();
        estadoAtual = 'pausado';
        tocarBip(440, 90);
        document.getElementById('txtBotao').innerText = "⏸️ PAUSADO (2 TOQUES P/ VOLTAR)";
      } else if (estadoAtual === 'pausado') {
        // Se já estava pausado e deu mais 1 toque, é porque quer dar um NOVO comando por voz!
        tocarBip(660, 90);
        iniciarEscuta();
      } else if (estadoAtual === 'ouvindo') {
        // Cancela a escuta
        pararMicrofone();
        estadoAtual = 'ocioso';
        document.getElementById('txtBotao').innerText = "🎙️ TOQUE PARA FALAR";
      } else {
        // Ocioso: inicia escuta de comando
        iniciarEscuta();
      }
    }

    function executarAcaoDuploToque() {
      if (estadoAtual === 'pausado') {
        // Retoma exatamente de onde parou!
        tocarBip(880, 120);
        audioAtual.play().then(() => {
          estadoAtual = 'falando';
          document.getElementById('txtBotao').innerText = "🔊 LENDO... (1 TOQUE P/ PAUSAR)";
        }).catch(() => {
          iniciarEscuta();
        });
      } else if (estadoAtual === 'falando') {
        // Se der dois toques enquanto fala, apenas confirma e continua lendo
        tocarBip(880, 80);
      } else {
        // Se estava ocioso, abre escuta
        iniciarEscuta();
      }
    }

    async function falarComVozHumana(texto) {
      if (!texto) return;

      if (audioAtual) {
        audioAtual.pause();
        audioAtual.currentTime = 0;
      }
      if (blobUrlAtual) {
        URL.revokeObjectURL(blobUrlAtual);
        blobUrlAtual = null;
      }

      estadoAtual = 'falando';
      const btn = document.getElementById('btnVoz');
      const txt = document.getElementById('txtBotao');
      btn.classList.add('carregando');
      txt.innerText = "⏳ GERANDO VOZ HUMANA...";

      try {
        const res = await fetch('/falar-audio', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ texto: texto })
        });

        if (!res.ok) throw new Error("Erro na síntese neural.");

        const blob = await res.blob();
        blobUrlAtual = URL.createObjectURL(blob);
        audioAtual.src = blobUrlAtual;

        btn.classList.remove('carregando');
        txt.innerText = "🔊 LENDO... (1 TOQUE P/ PAUSAR)";

        audioAtual.onended = () => {
          estadoAtual = 'ocioso';
          txt.innerText = "🎙️ TOQUE PARA FALAR";
          if (blobUrlAtual) {
            URL.revokeObjectURL(blobUrlAtual);
            blobUrlAtual = null;
          }
        };

        audioAtual.onerror = () => {
          btn.classList.remove('carregando');
          txt.innerText = "🎙️ TOQUE PARA FALAR";
          estadoAtual = 'ocioso';
        };

        await audioAtual.play();
      } catch (err) {
        btn.classList.remove('carregando');
        txt.innerText = "🎙️ TOQUE PARA FALAR";
        estadoAtual = 'ocioso';
      }
    }

    async function processarComando(comando) {
      processando = true;
      if (audioAtual) {
        audioAtual.pause();
        audioAtual.currentTime = 0;
      }
      pararMicrofone();

      const btn = document.getElementById('btnVoz');
      const txt = document.getElementById('txtBotao');
      document.getElementById('txtComando').innerText = '"' + comando + '"';
      btn.classList.add('carregando');
      txt.innerText = "⏳ BUSCANDO NO JW.ORG...";

      try {
        const res = await fetch('/comando', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comando })
        });
        const data = await res.json();
        const resposta = data.resposta_falada;
        document.getElementById('txtResposta').innerText = resposta;
        processando = false;
        btn.classList.remove('carregando');
        await falarComVozHumana(resposta);
      } catch (err) {
        processando = false;
        btn.classList.remove('carregando');
        await falarComVozHumana("Não foi possível conectar ao servidor. Por favor, tente novamente.");
      }
    }

    window.addEventListener('load', () => {
      setTimeout(() => {
        falarComVozHumana("Assistente acessível pronto. Toque na tela para falar.");
      }, 500);
    });
  </script>
</body>
</html>
    """

@app.post("/comando", response_model=ComandoResponse)
async def receber_comando_voz(dados: ComandoRequest):
    if not dados.comando or not dados.comando.strip():
        raise HTTPException(status_code=400, detail="O comando de voz está vazio.")
    texto = dados.comando.strip()
    resposta = await assistente.processar_comando(texto)
    return ComandoResponse(comando_reconhecido=texto, resposta_falada=resposta)
