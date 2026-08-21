# PANDUAN DAN CAKUPAN PENGERJAAN CODEBASE AI CLOUD
## Project Guidelines, Architecture & Pure Codebase Scope (Antigravity Development)

---

## 1. PENDAHULUAN & RUANG LINGKUP CODEBASE (CODEBASE SCOPE)
Dokumen ini disusun sebagai panduan teknis mutlak untuk membangun **Codebase AI Cloud (Cloud AI Tier)** pada proyek **TelcoCare Smart Home Orchestrator** di dalam platform Google Antigravity. 

Fokus dari dokumen ini dibatasi secara ketat hanya pada **pembangunan arsitektur kode, struktur folder, logika penalaran (Reasoning Engine), integrasi alat eksekusi (Tools), dan gateway komunikasi aman**. Seluruh proses pengujian (testing), evaluasi model, serta pelatihan (training/fine-tuning LoRA) berada di luar cakupan dokumen ini dan akan ditangani pada sesi terpisah.

---

## 2. ARSITEKTUR KOMUNIKASI & ALIRAN DATA AI CLOUD

AI Cloud bertindak sebagai orkestrator pusat yang menerima input bahasa alami dari pengguna, menganalisis kondisi jaringan rumah (*state*), dan memicu tindakan fisik di tingkat router lokal (*CPE*) melalui pengiriman perintah JSON yang deterministik dan kaku.

### A. Pembagian Batas Sistem (TR-142 Compliance)
Untuk menjamin keamanan dan kestabilan transmisi fisik serat optik operator, AI Cloud hanya berkomunikasi secara eksklusif dengan **Residential Gateway (RG) Entity** (Layer 3 ke atas) melalui sambungan HTTPS/gRPC aman. AI Cloud dilarang berinteraksi langsung atau mengganggu parameter fisik **ONU Entity** (Layer 2) yang bersifat immutable (dilindungi).

```
+-------------------------------------------------------------------------------+
|                       PRIVATE CLOUD DATA CENTER OPERATOR                      |
|                                                                               |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
|   |   OpenAPI Server  | ───► | LangGraph Reasoning | ───►|  Outlines JSON |   |
|   |  (FastAPI Gateway)|      |   Engine (State)    |     |  Enforcement   |   |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
+─────────────────────────────────────────┬─────────────────────────────────────+
                                          │
                                          │ Kirim Perintah JSON Aman (gRPC/HTTPS)
                                          ▼
+-------------------------------------------------------------------------------+
|                      RG ENTITY (Layer 3+ Router OpenWrt CPE)                   |
|                                                                               |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
|   |  Local API Client | ───► |   Kernel Linux tc   | ───►| Firewall Rules |   |
|   | (Instruksi Parser)|      |  (QoS Queue Boost)  |     |   (nftables)   |   |
|   +───────────────────+      +─────────────────────+     +────────────────+   |
+-------------------------------------------------------------------------------+
```

### B. Aliran Komunikasi Reaktif (Control Loop Flow)
1.  **Dashboard Integration:** Aplikasi ponsel mengirimkan perintah mentah pengguna ke server backend Cloud (`api/routes/control.py`).
2.  **State Evaluation:** Agen LangGraph (`agent/graph.py`) membaca *working state* router guna mengambil profil koneksi dan daftar perangkat aktif.
3.  **Action Determination:** LLM memutuskan alat (*Actionable Tool*) mana yang harus dipanggil di dalam sub-direktori `agent/tools/`.
4.  **Schema Enforcement:** Pustaka *Outlines* memotong ruang kreatif LLM dan memaksanya mengeluarkan output JSON yang kaku, terstruktur, dan tervalidasi skema.
5.  **Edge Delivery:** Payload JSON yang telah bersih dikirim secara aman melalui SSL ke API router lokal untuk segera dieksekusi di level kernel Linux.

---

## 3. STRUKTUR FOLDER JALUR UTAMA (MONOREPO CODEBASE)

Penyusunan codebase AI Cloud mengadopsi prinsip modularitas tinggi dari platform agen skala besar (**Dify**) serta pola pemeliharaan memori stateful (**LangGraph**). Folder pelatihan (*training/*) dan skrip pengujian (*tests/*) dibuang sepenuhnya dari cakupan direktori ini:

```text
cloud-ai-orchestrator/              # Repositori Utama AI Cloud di Data Center Telco
├── api/                            # API Gateway Layer (FastAPI / gRPC)
│   ├── main.py                     # Entrypoint utama server FastAPI
│   ├── routes/                     # Endpoint komunikasi data
│   │   ├── telemetry.py            # Penerima telemetry dari router (Privacy-by-Design)
│   │   ├── control.py              # Penerima input bahasa alami dari Mobile App / Dashboard
│   │   └── webhooks.py             # Webhook trigger dari sistem pihak ketiga (Billing/IoT Cloud)
│   └── middleware/                 # Autentikasi token, enkripsi SSL/TLS, & rate limiter
│
├── agent/                          # Engine Penalaran Stateful (LangGraph Core)
│   ├── state.py                    # Definisi Short-term (Working) & Long-term state jaringan
│   ├── graph.py                    # Logika transisi state machine & loop ReAct
│   ├── nodes.py                    # Handler pemanggilan node (LLM Node, Action Execution Node)
│   ├── prompt_templates.py         # Kumpulan system prompt spesialis telekomunikasi & kontrol
│   └── tools/                      # Eksekutor aksi otonom (Actionable Tools)
│       ├── router_cmd.py           # Pembuat JSON perintah kernel QoS/nftables ke Edge CPE
│       ├── iot_control.py          # Adapter pengontrol perangkat Matter & Cloud Tuya API
│       └── billing_vas.py          # Integrator sistem penagihan tambahan pelanggan (Billing VAS)
│
├── core/                           # Lapisan Keamanan & Penjamin Output (LLMOps)
│   ├── schema.py                   # Penegak skema JSON kaku menggunakan Outlines / Instructor
│   └── security.py                 # Filter guardrails kognitif pencegah injeksi perintah sistem
│
├── integrations/                   # Driver Jaringan Operator & API Pihak Ketiga
│   ├── billing_client.py           # Penghubung internal ke sistem Core Billing operator
│   └── tuya_client.py              # Konektor integrasi Cloud-to-Cloud dengan Tuya IoT SDK
│
└── docker/                         # Konfigurasi Lingkungan Runtime Server
    ├── docker-compose.yaml         # Orkestrasi database PostgreSQL, Redis Cache, & server API
    └── .env.example                # Templat konfigurasi API keys & kredensial database
```

---

## 4. CAKUPAN PENGERJAAN TIM (DEVELOPMENT SCOPE BY COMPONENT)

### A. API Gateway Layer (`api/`)
*   **API Engine (`main.py`):** Menggunakan FastAPI untuk menginisiasi server asinkron berlatensi rendah.
*   **Telemetry Route (`routes/telemetry.py`):** Menyediakan port aman untuk menerima ringkasan telemetri dari router rumah tanpa membaca data sensitif paket data pengguna (*Privacy-by-Design*).
*   **Control Route (`routes/control.py`):** Menerima pesan string teks bebas dari pengguna dan meneruskannya ke LangGraph Engine.

### B. LangGraph Reasoning Engine (`agent/`)
*   **State Definition (`state.py`):** Mendefinisikan class `RouterState` berbasis Pydantic yang menyimpan:
    *   `messages`: Riwayat chat dengan pengguna.
    *   `active_devices`: List MAC & IP address aktif di rumah.
    *   `qos_policy`: Aturan prioritas trafik yang sedang berjalan saat ini.
    *   `security_status`: Status ancaman/isolasi perangkat IoT.
*   **Graph Orchestrator (`graph.py`):** Membangun graph state machine berisi simpul keputusan (*decision nodes*) dan simpul eksekusi (*tool execution nodes*) menggunakan loop **Reasoning and Acting (ReAct)**.
*   **Tools Library (`tools/`):** Menyediakan set fungsi Python yang dapat dipanggil secara otomatis oleh LLM untuk memicu aksi:
    *   `router_cmd.py` memformulasikan instruksi QoS tingkat kernel (misal: mematikan lag game/meningkatkan kecepatan video kerja) menjadi JSON yang dapat dipahami router lokal.
    *   `iot_control.py` merumuskan instruksi nyala/mati/redup untuk lampu atau kunci pintar Matter/Tuya.

### C. Output Sanitizer & Guardrails (`core/`)
*   **Deterministic Output Engine (`schema.py`):** Membungkus pemanggilan LLM Qwen dengan pustaka *Outlines* untuk memastikan format keluaran yang dihasilkan selalu berupa JSON valid yang mematuhi skema Pydantic:
    ```json
    {
      "target_action": "SET_TRAFFIC_PRIORITY",
      "target_mac": "A4:C3:F0:12:89:AB",
      "priority_class": "WORK_EF",
      "duration_minutes": 60,
      "narrative_response": "Prioritas jaringan untuk laptop kerja diaktifkan selama 1 jam."
    }
    ```
*   **Security Guardrails (`security.py`):** Melakukan pemeriksaan string sebelum JSON dikirimkan ke router untuk mencegah celah keamanan injeksi perintah shell (*OS Command Injection*) pada interpreter router OpenWrt.

---

## 5. ATURAN PENULISAN KODE UTAMA (GUIDELINES)
1.  **Strict Privacy Enforcement:** Codebase AI Cloud dilarang keras menerima, memproses, atau menyimpan data mentah sensitif pengguna (seperti riwayat pencarian web, payload paket data penuh, video, atau rekaman suara mentah). Hanya status numerik teranonimisasi dan perintah teks langsung pengguna yang boleh diproses.
2.  **No Naked AI Execution:** Jangan pernah mengizinkan LLM mengirim teks bebas tanpa format langsung ke router lokal. Seluruh instruksi jaringan wajib melalui penegakan skema (Schema Enforcement) di modul `core/schema.py` dan divalidasi ulang sebelum dikirim.
3.  **Isolation from Fiber Layer:** Codebase AI Cloud didesain hanya untuk mengirimkan instruksi kontrol IP (Layer 3) ke RG Entity. Jauhi penulisan fungsionalitas yang menyentuh ranah ONU Entity fisik (registrasi optik Layer 2) untuk mencegah pemutusan koneksi fisik serat optik massal.
