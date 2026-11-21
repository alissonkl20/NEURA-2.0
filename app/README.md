# NEURACHAT — Sophia

Assistente de IA utilizando Mistral 7B, Python, Ollama e Docker.

## 📁 Estrutura do projeto

app/ ├── Dockerfile ├── README.md ├── config.py ├── controller.py ├── requirements.txt ├── service.py ├── shell.py ├── data_books/ └── docker/ └── docker-compose.yml


## 🐳 Docker

Todos os comandos abaixo devem ser executados na pasta `app/docker`.

### Entrar na pasta do Docker

cd ~/Documentos/NEURACHAT/app/docker


### Iniciar o NEURACHAT

Construir a imagem, se necessário, e iniciar os serviços:

sudo docker compose up -d --build


### Verificar o estado dos containers

sudo docker compose ps


### Visualizar os logs

sudo docker compose logs -f neurachat


Para sair da visualização, pressione `Ctrl + C`.

### Reiniciar o container

sudo docker compose restart neurachat


### Parar os serviços

sudo docker compose stop


### Iniciar novamente os serviços parados

sudo docker compose start


### Parar e remover os containers

sudo docker compose down


Os arquivos do projeto e o diretório `data_books` são preservados.

### Reconstruir a imagem sem cache

sudo docker compose down sudo docker compose build --no-cache sudo docker compose up -d


### Remover também a imagem local do projeto

sudo docker compose down --rmi local sudo docker compose build --no-cache sudo docker compose up -d


Atenção: isso remove a imagem local associada ao projeto. Não remove automaticamente todos os modelos do Ollama.

## 🤖 Shell interativo da Sophia

Se o container estiver ativo e o shell não estiver sendo executado automaticamente:

sudo docker compose exec neurachat python -u /app/shell.py


O shell permite enviar mensagens para a Sophia e receber respostas em streaming.

As métricas exibidas incluem:

- TTFT: tempo até o primeiro token.
- Tokens: quantidade de tokens gerados.
- Tempo: duração total da geração.
- Velocidade: tokens por segundo.

Se o shell já estiver rodando como processo principal do container, não execute esse comando para iniciar uma segunda instância sem necessidade.

## 📱 Acesso pelo Termux via SSH

No Android, conecte-se ao PC:

ssh alisson@IPDOSEU_PC


Substitua `IP_DO_SEU_PC` pelo endereço IP do computador.

Depois de conectar:

cd ~/Documentos/NEURACHAT/app/docker


Verifique o container:

sudo docker compose ps


Se o container estiver ativo, mas o shell não estiver rodando:

sudo docker compose exec neurachat python -u /app/shell.py


A autenticação SSH por chave pode evitar a necessidade de informar a senha da conta a cada conexão.

## ⚙️ Configuração

O Docker Compose utiliza:

- Serviço: `neurachat`
- Container: `neurachat-app`
- Rede: `host`
- Ollama: `http://127.0.0.1:11434`
- Diretório persistente: `data_books`

O Ollama deve estar acessível no endereço configurado.

## 🔧 Diagnóstico

### Verificar os containers

sudo docker ps -a


### Verificar os logs

sudo docker compose logs --tail=100 neurachat


### Verificar o Docker

sudo systemctl status docker


### Iniciar o serviço Docker

sudo systemctl enable --now docker


### Validar o Compose

sudo docker compose config


### Abrir um terminal dentro do container

sudo docker compose exec neurachat bash


Se `bash` não estiver instalado, tente:

sudo docker compose exec neurachat sh


## ⚠️ Observações

- Execute os comandos do Compose na pasta `app/docker`.
- Não remova o diretório `data_books` durante uma limpeza sem verificar seu conteúdo.
- Não compartilhe chaves privadas SSH.
- Evite executar comandos de remoção global do Docker sem verificar quais imagens, containers e volumes serão afetados.
- O comando `docker compose down` não apaga os arquivos do código-fonte.

---
Projeto NEURACHAT — Sophia

Salve com Ctrl + O, pressione Enter e saia com Ctrl + X.
Conferir o README

Execute:

cat ~/Documentos/NEURACHAT/app/README.md

Atalhos úteis para o dia a dia

Depois de criar o README, estes são os três comandos que você provavelmente mais utilizará:

Iniciar ou reconstruir:

cd ~/Documentos/NEURACHAT/app/docker && sudo docker compose up -d --build

Acompanhar os logs:

cd ~/Documentos/NEURACHAT/app/docker && sudo docker compose logs -f neurachat

Reiniciar:

cd ~/Documentos/NEURACHAT/app/docker && sudo docker compose restart neurachat