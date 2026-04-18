# Gerência de Usuários

Ferramenta web interna para gerenciar usuários em servidores Linux remotos via SSH ou Telnet. Feita com Django, roda direto no navegador — sem cliente instalado, sem copiar scripts.

A ideia surgiu da necessidade de padronizar e agilizar operações administrativas recorrentes sem precisar abrir terminal, lembrar de comandos ou correr o risco de erro de digitação.

---

## O que faz

| Operação | Descrição |
|---|---|
| Adicionar usuário | Cria o usuário com senha e grupo no servidor remoto |
| Alterar senha | Redefine a senha de um usuário existente |
| Alterar grupo | Muda o grupo principal do usuário |
| Excluir usuário | Remove o usuário **e** o home permanentemente |

O operador escolhe o protocolo (SSH ou Telnet) e informa o host/porta direto na tela — sem precisar mexer em arquivo de configuração.

---

## Stack

- **Backend:** Django 4.2 + Gunicorn
- **Conectividade:** Paramiko (SSH) / telnetlib (Telnet)
- **Frontend:** HTML + CSS + JS puro (sem framework)
- **Proxy / estáticos:** Nginx
- **Sessão:** File-based (sem banco de dados)
- **Deploy:** Docker Compose (dois containers: app + nginx)

---

## Subindo com Docker (recomendado)

```bash
# 1. Copiar e editar as variáveis de ambiente
cp .env.example .env

# 2. Subir
docker compose up -d --build
```

Acesse: **http://\<IP-do-host\>**

Para ver os logs:
```bash
docker compose logs -f
```

Para parar:
```bash
docker compose down
```

---

## Rodando localmente (desenvolvimento)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

pip install -r requirements.txt

cp .env.example .env
# editar .env

python manage.py runserver
```

Acesse: **http://127.0.0.1:8000**

---

## Variáveis de ambiente (`.env`)

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | sim | — | Chave secreta Django — gere uma aleatória |
| `DEBUG` | não | `False` | `True` apenas em desenvolvimento |
| `ALLOWED_HOSTS` | sim (prod) | `*` | Hosts permitidos, separados por vírgula |
| `CSRF_TRUSTED_ORIGINS` | sim (atrás de proxy) | — | Ex: `http://10.0.0.50` |
| `SSH_HOST` | não | — | Pré-preenche o campo de host no frontend |
| `SSH_PORT` | não | `22` | Porta SSH padrão |
| `TELNET_PORT` | não | `23` | Porta Telnet padrão |
| `CMD_SU_LOGIN` | não | `su -` | Comando de elevação de privilégio |
| `CMD_CREATE_USER` | não | `useradd ...` | Comando de criação de usuário |
| `CMD_CHANGE_PASSWORD` | não | `chpasswd ...` | Comando de alteração de senha |
| `CMD_CHANGE_GROUP` | não | `usermod ...` | Comando de alteração de grupo |
| `CMD_DELETE_USER` | não | `userdel -r ...` | Comando de exclusão de usuário |

Os comandos aceitam os placeholders `{username}`, `{password}` e `{group}`.

---

## Endpoints

| Método | URL | Descrição |
|---|---|---|
| `GET` | `/` | Página principal |
| `POST` | `/login/` | Conecta via SSH ou Telnet |
| `POST` | `/execute/` | Executa operação administrativa |
| `POST` | `/logout/` | Encerra a sessão |
| `POST` | `/groups/` | Lista grupos disponíveis no servidor |

---

## Estrutura

```
cmm_cmu/
├── Dockerfile
├── docker-compose.yml
├── nginx/
│   └── default.conf
├── manage.py
├── requirements.txt
├── .env.example
├── .dockerignore
├── config/
│   ├── settings.py          # Configurações — lê variáveis do .env
│   ├── urls.py
│   └── wsgi.py
├── app/
│   ├── views.py             # index, ssh_login, execute_action, ssh_logout, list_groups
│   ├── forms.py             # LoginForm (protocol, host, port, user, pass), OperationForm
│   ├── urls.py
│   └── services/
│       ├── ssh_service.py       # Paramiko — SSH interativo com su
│       ├── telnet_service.py    # telnetlib — Telnet interativo com su
│       └── command_builder.py   # Monta comandos com shlex.quote (sanitização)
├── templates/app/
│   └── index.html
└── static/app/
    ├── css/style.css
    └── js/app.js
```

---

## Notas de segurança

- As credenciais ficam na sessão do servidor **somente durante a sessão ativa** e são apagadas ao desconectar ou após 1 hora de inatividade.
- Todos os valores inseridos pelo usuário passam por `shlex.quote()` antes de compor o comando remoto.
- O `DEBUG` deve ser `False` em produção — com `True`, Django pode expor informações sensíveis em páginas de erro.
- O `.env` nunca deve entrar na imagem Docker (já está no `.dockerignore`).


## Funcionalidades

| Aba | Ação | Descrição |
|-----|------|-----------|
| Adicionar | Criar usuário | Cria o usuário com senha e grupo no servidor remoto |
| Alterar Senha | Alterar senha | Redefine a senha de um usuário existente |
| Alterar Grupo | Alterar grupo | Altera o grupo principal do usuário |
| Excluir Usuário | Excluir | Remove o usuário e o diretório home permanentemente |

Os comandos remotos são totalmente configuráveis via variáveis de ambiente (`.env`). Os padrões são:

| Variável | Comando padrão |
|----------|---------------|
| `CMD_CREATE_USER` | `useradd -m -s /bin/bash -G {group} {username} && echo {username}:{password} \| chpasswd` |
| `CMD_CHANGE_PASSWORD` | `echo {username}:{password} \| chpasswd` |
| `CMD_CHANGE_GROUP` | `usermod -g {group} {username}` |
| `CMD_DELETE_USER` | `userdel -r {username}` |
| `CMD_SU_LOGIN` | `su -` |

## Stack

- **Backend:** Django 4.2 + Paramiko (SSH)
- **Frontend:** Django Templates + HTML / CSS / JavaScript (sem framework)
- **Sessão:** File-based (sem banco de dados)
- **Autenticação:** Credenciais SSH validadas a cada operação (não armazenadas em BD)

## Instalação

```bash
# 1. Ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 2. Dependências
pip install -r requirements.txt

# 3. Variáveis de ambiente
copy .env.example .env       # edite conforme necessário
```

### Variáveis de ambiente obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SSH_HOST` | IP ou hostname do servidor remoto | `192.168.1.10` |
| `DJANGO_SECRET_KEY` | Chave secreta Django | string aleatória longa |

### Variáveis opcionais

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `SSH_PORT` | `22` | Porta SSH |
| `DEBUG` | `True` | Modo debug Django |
| `CMD_SU_LOGIN` | `su -` | Comando de elevação para root |
| `CMD_CREATE_USER` | (ver acima) | Comando de criação de usuário |
| `CMD_CHANGE_PASSWORD` | (ver acima) | Comando de alteração de senha |
| `CMD_CHANGE_GROUP` | (ver acima) | Comando de alteração de grupo |
| `CMD_DELETE_USER` | (ver acima) | Comando de exclusão de usuário |

```bash
# 4. Executar
python manage.py runserver
```

Acesse: **http://127.0.0.1:8000**

## Endpoints

| Método | URL | Descrição |
|--------|-----|-----------|
| `GET` | `/` | Página principal (SPA) |
| `POST` | `/login/` | Autenticação SSH |
| `POST` | `/execute/` | Executa uma operação administrativa |
| `POST` | `/logout/` | Encerra a sessão |
| `POST` | `/groups/` | Lista grupos disponíveis no servidor |

## Estrutura

```
cmm_cmu/
├── manage.py
├── requirements.txt
├── .env
├── config/                  # Configuração Django
│   ├── settings.py          # Lê .env; define SSH_HOST, SSH_PORT, CMD_*
│   ├── urls.py
│   └── wsgi.py
├── app/                     # Aplicação principal
│   ├── views.py             # Views: index, ssh_login, execute_action, ssh_logout, list_groups
│   ├── forms.py             # LoginForm, OperationForm
│   ├── urls.py
│   └── services/
│       ├── ssh_service.py       # Paramiko: test_ssh_connection, run_ssh_command, run_command_via_su, check_is_root
│       └── command_builder.py   # Monta comandos remotos com shlex.quote
├── templates/app/
│   └── index.html           # Interface única (SPA)
└── static/app/
    ├── css/style.css
    └── js/app.js            # Lógica de UI: tabs, modais, fetch, toggle senha, print resultado
```

## Fluxo da Aplicação

### Autenticação
1. Usuário informa suas credenciais SSH (usuário + senha) no painel de conexão.
2. O backend valida via `test_ssh_connection` (Paramiko).
3. Detecta automaticamente se o usuário é root (`id -u == 0`).
4. Sessão é criada com as credenciais e flag `is_root`.

### Execução de Operações
- **Usuário root:** o comando é executado diretamente via `run_ssh_command`.
- **Usuário não-root:** um modal solicita a senha root; o backend usa `run_command_via_su` para elevar privilégios via `su -`.
- Grupos são validados antes de criar ou alterar usuário (`/etc/group`).
- Em caso de grupo inexistente, o frontend oferece listar os grupos disponíveis.

### Interface
- Botão de mostrar/ocultar senha dentro dos campos de senha e confirmar senha.
- Resultado do comando exibido em console estilizado.
- Botão de imprimir o resultado do comando (abre janela de impressão do navegador).
- Confirmação modal antes de excluir usuários.
