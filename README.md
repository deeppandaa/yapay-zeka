# LocalQwenAgent

Local browser-based Qwen workspace for coding, document analysis, and project memory.

# Llama Cpp & Ollama Bridge with Agentic RAG

A local AI bridge and agentic workspace integration built for **DeepPanda**. 

### Key Features
- **Offline-First Hybrid Architecture:** Uses Qwen models for local inference and fallback web search execution.
- **Tool Calling Mechanism:** Automatically triggers web searches or internal tools when local context is insufficient.
- **VS Code Copilot Integration:** Fully compatible with VS Code extensions (Continue, Twinny) via standard local endpoints (`http://127.0.0.1:8787.`).
- **Zero Data Leakage:** Ensures 100% privacy by keeping code completion, context analysis, and agentic reasoning on the local machine.

## Current capabilities

- Local Ollama chat through a browser UI
- PDF and text upload with bounded extraction
- Image upload for vision-capable Ollama models
- SQLite memory for explicit user notes
- Read-only workspace context lookup
- No automatic shell execution or file mutation in the first version
- Guarded agent tools: workspace-only writes, backup-before-write, and explicit command approval
- Video/audio pipeline: FFmpeg extraction and optional local faster-whisper transcription
- Public GitHub research with persistent learning notes

`MAX_UPLOAD_MB=0` local uploads are unlimited by application policy. Large PDFs are still limited by available disk/RAM because PDF extraction currently processes the file locally.

## Start on Windows

```powershell
cd C:\Users\emre\Desktop\DeepPanda-Proje\Yapay Zeka
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
ollama serve
ollama pull qwen3.6:latest
python app.py
```

Open http://127.0.0.1:8787.

## VS Code local bridge

The agent also exposes an OpenAI-compatible endpoint for local VS Code clients:

- Base URL: `http://127.0.0.1:8787/v1`
- Model: `local-qwen`
- Chat endpoint: `http://127.0.0.1:8787/v1/chat/completions`
- Models endpoint: `http://127.0.0.1:8787/v1/models`

For clients that ask for an API key, use any local placeholder value; the bridge does not authenticate requests on loopback. Keep the endpoint bound to `127.0.0.1` unless authentication and access control are added first.

### Continue configuration

In Continue's local `config.yaml`, add:

```yaml
name: LocalQwenAgent
version: 1.0.0
schema: v1
models:
	- name: local-qwen
		provider: openai
		model: local-qwen
		apiBase: http://127.0.0.1:8787/v1
		apiKey: local-only
```

Start Ollama and LocalQwenAgent before using the model in Continue. Continue then sends chat requests to the local agent, while the agent keeps its existing workspace context, approval rules, operation journal, and persistent memory.

The Ollama service must be running separately. The agent does not kill or install Ollama automatically.

Ollama models are kept in the runtime store under `Yapay Zeka\AI-Runtimes\OllamaModels`.

The agent does not silently execute commands or install packages. Commands require explicit approval, and writes are restricted to `WORKSPACE_ROOT` with backups.

## Eksik kutuphaneler

Agent icindeki `dependencies` profili iki onayli islem sunar:

- `check`: `.venv` paket uyumlulugunu kontrol eder.
- `install`: `requirements.txt` icindeki paketleri `.venv` icine kurar.

Kurulum kendiliginden baslamaz; once komut onizlenir ve kullanici onayi gerekir. Yeni bilgisayarda toplu kurulum icin `setup_portable.ps1` kullanilabilir.

Ogrenme notlarini kaydetmeden once onay istemek icin `.env` icinde `REQUIRE_MEMORY_APPROVAL=on` yapin. Chat isteginde `approve_memory=true` gelmeden not `memory.db` dosyasina yazilmaz.

Embedding modeli yoksa `/api/embedding/status` kurulum komutunu gosterir. `/api/embedding/prepare` endpoint'i `approved=false` ile sadece onay ister; `approved=true` olmadan `ollama pull nomic-embed-text` calistirilmaz.

OCR icin `/api/ocr/status` eksik Python baglayicisini ve Tesseract motorunu bildirir. `/api/ocr/prepare` onay olmadan kurulum yapmaz; Windows motoru icin `winget install --id UB-Mannheim.TesseractOCR -e` komutunu gosterir.

Tum eksik kurulumlari tek planda gormek icin `/api/setup/status`, onayli kurulum icin `/api/setup/prepare` kullanilir. `approved=false` sadece komut planini gosterir; `approved=true` Python paketlerini, Chromium'u, Qwen/embedding modellerini ve OCR motorunu sirayla kurar. Bir adim basarisiz olursa sonraki adimlara gecmez.

Continue ayarini otomatik yedekleyip kurmak icin `Setup-ContinueConfig.cmd` dosyasina cift tiklayin. Mevcut `C:\Users\emre\.continue\config.yaml` once tarihli `.bak` dosyasina kopyalanir.

## Move to another computer

Copy the entire `DeepPanda-Proje` folder, then run `setup_portable.ps1` from its `Yapay Zeka` subfolder. Do not copy `.venv`; the script recreates it for the new Python installation. `memory.db` travels with the folder. Ollama itself must be installed separately, and the model files must either be copied under `Yapay Zeka\AI-Runtimes\OllamaModels` or pulled again with `ollama pull`.

## Geri yukleme

Yeni bilgisayarda veya yedekten donerken `Restore-DeepPandaAI.cmd` dosyasina cift tiklayin. Kaynak `DeepPanda-Proje` klasorunu sorar; mevcut `Yapay Zeka` klasorunu `.localqwen-restore-backups` altina yedekler, sonra kaynakta bulunan AI kodunu, `memory.db` dosyasini ve model/runtime verilerini geri getirir. `.venv`, cache ve loglar ezilmez. Geri yukleme sonrasi `Start-LocalQwenAgent.cmd` dosyasini calistirin.

Tek komutla yedek almak icin `Export-DeepPandaAI.cmd` dosyasina cift tiklayin. Varsayilan paket kodu, ayarlari ve `memory.db` dosyasini icerir; modelleri de dahil etmek icin `Export-DeepPandaAI.cmd -IncludeModels` kullanin. Restore scripti `.zip` paketlerini dogrudan acar ve kurulum sonrasi compile/test self-audit raporu uretir.

## Safety model

The first version only reads selected workspace files and stores explicit memory notes. Internet research, package installation, and code edits will require separate approved tools and audit logging.
