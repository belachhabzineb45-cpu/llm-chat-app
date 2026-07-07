# Assistant IA — Chat LLM avec login (Python + React + Gemma)

Application full-stack de chat IA, **100 % gratuite et locale** :

- **Backend** : Python (FastAPI) — authentification sécurisée (mots de passe hachés PBKDF2, sessions JWT, base SQLite)
- **Frontend** : React (Vite) — écran de connexion / inscription + interface de chat
- **Modèle** : Gemma (modèle open source de Google), exécuté localement via Ollama — aucune clé API, aucun abonnement, les conversations ne quittent jamais la machine

## Structure du projet

```
llm-chat-app/
├── backend/
│   ├── main.py            # API : /register, /login, /me, /chat (→ Ollama)
│   └── requirements.txt
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── index.css
        └── App.jsx        # Login + chat
```

---

# 🪟 Lancer sur Windows (PC local)

## Prérequis (une seule fois)

1. **Python** : https://www.python.org/downloads/ — cocher **« Add Python to PATH »** à l'installation
2. **Node.js** (version LTS) : https://nodejs.org
3. **Ollama** : https://ollama.com/download → OllamaSetup.exe

Puis télécharger le modèle (PowerShell) :

```powershell
ollama pull gemma3:1b     # ~800 Mo, léger et rapide
# Meilleure qualité (GPU/RAM suffisants) :  ollama pull gemma3  (4b, ~3,3 Go)
```

## Lancement — Terminal PowerShell n°1 : backend

```powershell
cd C:\Users\DELL\Downloads\llm-chat-app\backend

# Environnement virtuel (première fois seulement)
python -m venv venv

# Activer le venv (à refaire à chaque nouveau terminal)
.\venv\Scripts\Activate.ps1

# Dépendances (première fois seulement)
pip install -r requirements.txt

# Lancer le backend
uvicorn main:app --reload --port 8000
```

> ⚠️ Si `Activate.ps1` est bloqué (« execution of scripts is disabled ») :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> puis relancer l'activation.

## Lancement — Terminal PowerShell n°2 : frontend

```powershell
cd C:\Users\DELL\Downloads\llm-chat-app\frontend
npm install          # première fois seulement
npm run dev
```

## Accès

Ouvrir **http://localhost:5173** — créer un compte, puis discuter.

> Sur Windows, les deux terminaux doivent rester ouverts pendant l'utilisation.
> Vérifier que `frontend/src/App.jsx` contient bien `const API = "http://localhost:8000/api"`.

---

# 🐧 Lancer sur le serveur Linux (Ubuntu)

Exemple : projet dans `~/llm_conversationnel/`, serveur à l'IP `192.168.1.2`,
backend sur le port **5172**, frontend sur le port **5173**.

## Prérequis (une seule fois)

```bash
# Python + Node.js (dépôt NodeSource : nodejs inclut déjà npm)
apt update && apt install -y python3 python3-pip python3-venv nodejs

# Ollama + le modèle Gemma
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:1b
```

## Installation (une seule fois)

```bash
# Dépendances Python dans un venv
cd ~/llm_conversationnel
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Dépendances Node
cd frontend && npm install
```

Adapter les adresses pour l'accès depuis le réseau local :

```bash
# Le frontend doit appeler l'IP du serveur (et le port backend choisi)
sed -i 's|http://localhost:8000/api|http://192.168.1.2:5172/api|' ~/llm_conversationnel/frontend/src/App.jsx
```

## Lancement manuel (débogage)

```bash
# Terminal 1 — backend
cd ~/llm_conversationnel/backend
source ../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5172

# Terminal 2 — frontend
cd ~/llm_conversationnel/frontend
npm run dev -- --host 0.0.0.0
```

> `--host 0.0.0.0` est indispensable pour accéder depuis un autre appareil du réseau.

## Lancement permanent (services systemd — recommandé)

Créer les services (une seule fois) :

```bash
cat > /etc/systemd/system/llm-backend.service << 'EOF'
[Unit]
Description=LLM Chat Backend (FastAPI)
After=network.target ollama.service

[Service]
WorkingDirectory=/root/llm_conversationnel/backend
ExecStart=/root/llm_conversationnel/venv/bin/uvicorn main:app --host 0.0.0.0 --port 5172
Restart=always
Environment=JWT_SECRET=remplacez-par-le-resultat-de-openssl-rand-hex-32

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/llm-frontend.service << 'EOF'
[Unit]
Description=LLM Chat Frontend (Vite)
After=network.target

[Service]
WorkingDirectory=/root/llm_conversationnel/frontend
ExecStart=/usr/bin/npm run dev -- --host 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now llm-backend llm-frontend
```

Commandes du quotidien :

```bash
systemctl start llm-backend llm-frontend      # démarrer
systemctl stop llm-backend llm-frontend       # arrêter
systemctl restart llm-backend llm-frontend    # redémarrer (après modif du code)
systemctl is-active llm-backend llm-frontend ollama   # vérifier l'état

journalctl -u llm-backend -f                  # logs backend en direct
journalctl -u llm-frontend -f                 # logs frontend en direct

ss -tlnp | grep -E ':5172|:5173'              # vérifier les ports
```

> ⚠️ Ne pas lancer manuellement si les services tournent déjà : le port serait
> « address already in use ». Faire d'abord `systemctl stop llm-backend llm-frontend`.

## Accès

| Service | Port | Adresse |
|---|---|---|
| Interface web (utilisateurs) | 5173 | http://192.168.1.2:5173 |
| API backend (+ doc sur /docs) | 5172 | http://192.168.1.2:5172 |
| Ollama (Gemma) | 11434 | localhost uniquement (interne au serveur) |

Comptes utilisateurs : stockés dans `backend/app.db` (SQLite, mots de passe hachés).

```bash
sqlite3 ~/llm_conversationnel/backend/app.db "SELECT id, name, email FROM users;"
```

---

# Configuration (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `OLLAMA_MODEL` | `gemma3:1b` | Modèle local (`gemma3` = 4b meilleur, `gemma3:12b` encore mieux) |
| `OLLAMA_URL` | `http://localhost:11434` | Adresse d'Ollama |
| `JWT_SECRET` | aléatoire au démarrage | À fixer en prod (sinon déconnexions à chaque redémarrage) |
| `DB_PATH` | `app.db` | Fichier SQLite |

# Pour aller plus loin

- **Sauvegarde des conversations** en base (l'historique disparaît actuellement au rechargement)
- **Streaming** des réponses mot à mot
- **Build de production** du frontend (`npm run build` + reverse proxy nginx/Caddy)
- **Exposition sur internet** : HTTPS, nom de domaine, CORS restreint, utilisateur non-root
