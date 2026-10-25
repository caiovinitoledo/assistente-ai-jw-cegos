# 🎙️ Assistente de Voz Acessível JW

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Edge-TTS](https://img.shields.io/badge/Voz%20Neural-Francisca%20(pt--BR)-0078D4?style=for-the-badge&logo=microsoft)](https://github.com/rany2/edge-tts)
[![Acessibilidade](https://img.shields.io/badge/Acessibilidade-WCAG%20AAA-00A86B?style=for-the-badge)](https://www.w3.org/WAI/)
[![Deploy no Render](https://img.shields.io/badge/Render-Deploy%20Ativo-46E3B7?style=for-the-badge&logo=render)](https://render.com/)

> **Um assistente web e PWA de comando de voz e áudio contínuo projetado para permitir que pessoas cegas ou com baixa visão estudem e naveguem pelas matérias do [JW.ORG](https://www.jw.org) e pela Bíblia Sagrada com total autonomia, toque antiacidental e voz neural humanizada.**

---

## 🌟 O Desafio e a Solução

Pessoas cegas frequentemente enfrentam dificuldades para navegar em sites com layouts complexos, artigos longos, botões pequenos e interfaces poluídas. Além disso, leitores de tela convencionais usam vozes robóticas, e qualquer toque involuntário no celular costuma fechar a matéria ou perder o ponto de leitura.

O **Assistente Acessível JW** resolve esses problemas na raiz:
1. **Interface Zero-Visão**: Toda a tela do celular é transformada em duas grandes zonas táteis com contraste ultra-elevado.
2. **Máquina de Estados Anti-Toque Acidental**: Esbarrões na tela não interrompem o estudo. Um toque apenas pausa, dois toques rápidos retomam a leitura de onde parou, e um toque com o app em pausa abre a escuta para um novo comando.
3. **Voz Humana de Estúdio**: Utiliza a voz neural `pt-BR-FranciscaNeural` com ritmo calmo (`-5%`), proporcionando uma narração confortável e respeitosa.
4. **Expansão Bíblica em Tempo Real**: Sempre que uma citação bíblica abreviada aparece nos parágrafos (ex: *Is. 41:10*, *Pr. 27:11*, *Deut. 31:23*), o assistente a anuncia por extenso, lê o versículo integral da Tradução do Novo Mundo e retoma o parágrafo sem que o usuário precise fazer nada.
5. **Streaming de Áudio Gapless (Zero Delay)**: Pipeline com pré-carregamento por promessas em memória (*Lookahead Buffer*). A fala começa em menos de meio segundo e as transições entre parágrafos têm **0 segundos de espera**.

---

## 🚀 Principais Funcionalidades

### 📖 1. Estudo de A Sentinela da Semana
- Lê o artigo de estudo semanal completo ou salta direto para um parágrafo solicitado:
  - *"Ler A Sentinela da semana"*
  - *"Ler parágrafo 5 de A Sentinela"*

### 📚 2. Estudo Bíblico de Congregação (Livro Completo)
- Localiza cirurgicamente a matéria do livro em estudo na reunião de meio de semana (ex: capítulos do livro de Josué) e lê o conteúdo integral, expandindo todos os textos bíblicos citados:
  - *"Ler o estudo bíblico dessa semana"*
  - *"Ler o estudo de livro"*
  - *"Ler parágrafo 3 do estudo bíblico"*

### 📜 3. Leitura Semanal da Bíblia (Capítulos Inteiros)
- Acessa os capítulos completos da programação semanal que ficam no topo da reunião (ex: *Jeremias 45 e 46*):
  - *"Ler a leitura da Bíblia dessa semana"*
  - *"Capítulos da Bíblia da semana"*

### ☀️ 4. Texto Diário ("Examine as Escrituras")
- Lê o tema do dia, texto bíblico e comentário diário com versículos citados lidos na íntegra:
  - *"Ler o texto diário"*
  - *"Texto de hoje"*

### ✝️ 5. Leitura Direta de Qualquer Texto da Bíblia
- Busca instantânea na Tradução do Novo Mundo da Bíblia Sagrada no `wol.jw.org`:
  - *"Ler Salmos 83 18"*
  - *"Ler Isaías 41 versículo 10"*
  - *"Ler João 17 3"*

### 🔍 6. Pesquisa Temática
- Pesquisa artigos e tópicos no JW.ORG:
  - *"Pesquisar no JW sobre depressão"*
  - *"Pesquisar no JW sobre ressurreição"*

### 💡 7. Guia Acessível por Voz
- Instruções detalhadas sobre comandos e explicação do uso dos gestos táteis:
  - *"O que você pode fazer?"*
  - *"Como funciona?"*
  - *"Quais são os comandos?"*

---

## 🛠️ Arquitetura e Engenharia de Software

```
assistente-ai-jw-cegos/
├── main.py              # Aplicação FastAPI, rotas de áudio neural e frontend PWA
├── ai_agent.py          # Agente cognitivo, expansor bíblico e roteador de intenções
├── browser_service.py   # Web scraping assíncrono de alto desempenho no wol.jw.org (HTTP/2)
├── requirements.txt     # Dependências de produção
├── Procfile             # Configuração de inicialização no Render
└── .python-version      # Python 3.11.9
```

### ⚡ Destaques de Performance:
- **HTTP/2 Connection Pooling**: Substituição de navegadores pesados headless (Chromium) por requisições assíncronas com `httpx.AsyncClient` e `BeautifulSoup4`. Tempo de extração caiu de **25s para menos de 0,5s**.
- **Lookahead Buffer com Promises**: Textos longos são fragmentados em blocos (180 chars para início imediato e 420 chars para blocos seguintes). O navegador baixa até 2 blocos à frente na memória, eliminando qualquer pausa na transição entre partes.
- **Audiodescrição Acústica (Web Audio API)**: Emissão de bipes em frequências senoidais distintas (440Hz a 880Hz) para orientar o usuário cego sobre o status da aplicação sem necessidade de visão.

---

## 📱 Gestos da Tela (Acessibilidade Tátil)

| Ação do Usuário | Estado do App | Comportamento |
| :--- | :--- | :--- |
| **1 Toque** | Lendo áudio | **Pausa a leitura** sem perder a posição exata |
| **2 Toques Rápidos (<350ms)** | Pausado | **Retoma a reprodução** no mesmo instante |
| **1 Toque** | Pausado ou em Silêncio | **Abre o microfone** para escutar um novo comando |

---

## 💻 Como Rodar Localmente

### Pré-requisitos:
- Python 3.11+
- Git

### 1. Clonar o repositório:
```bash
git clone https://github.com/caiovinitoledo/assistente-ai-jw-cegos.git
cd assistente-ai-jw-cegos
```

### 2. Criar e ativar o ambiente virtual:
```bash
python -m venv venv

# No Windows:
venv\Scripts\activate

# No Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependências:
```bash
pip install -r requirements.txt
```

### 4. Iniciar o servidor:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Acesse no navegador:
- Aplicação PWA: `http://localhost:8000/` ou `http://localhost:8000/app`
- Documentação OpenAPI/Swagger: `http://localhost:8000/docs`

---

## 🌐 Deploy em Produção

O projeto é configurado para deploy instantâneo na nuvem [Render](https://render.com):
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Python Version**: Definida automaticamente como `3.11.9` pelo arquivo `.python-version`.

---

## 📄 Licença e Uso

Este projeto foi desenvolvido com finalidade social, educacional e de acessibilidade para a comunidade de pessoas com deficiência visual. As matérias bíblicas e publicações acessadas pertencem à *Watch Tower Bible and Tract Society of Pennsylvania*.
