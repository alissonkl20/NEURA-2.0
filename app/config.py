"""
Configuração do modelo Mistral 7B via Ollama + Unsloth para fine-tuning.
Hardware alvo: GPU com 12GB VRAM.
"""

import os
from pathlib import Path

# ===== Diretórios =====
BASE_DIR = Path(__file__).resolve().parent
DATA_BOOKS_DIR = BASE_DIR / "data_books"
SKILLS_DIR = DATA_BOOKS_DIR / "skills"
SESSIONS_DIR = DATA_BOOKS_DIR / "sessions"
CORPUS_FILE = DATA_BOOKS_DIR / "corpus.txt"

# ===== Modelo =====
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
OLLAMA_MODEL = "mistral:7b"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# ===== Contexto =====
MAX_CONTEXT = 4096

# ===== Parâmetros de Inferência =====
GENERATION_CONFIG = {
    "temperature": 0.5,
    "top_p": 0.9,
    "top_k": 40,
    "max_tokens": 1024,
    "num_ctx": MAX_CONTEXT,
    "repeat_penalty": 1.1,
    "stream": True,
}

# ===== Parâmetros de Treinamento (Unsloth + LoRA) =====
TRAINING_CONFIG = {
    "max_seq_length": MAX_CONTEXT,
    "load_in_4bit": True,
    "load_in_16bit": False,
    "fp16": True,
    "bf16": False,
    "lora_r": 16,
    "lora_alpha": 16,
    "lora_dropout": 0.0,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    "bias": "none",
    "use_gradient_checkpointing": "unsloth",
    "random_state": 3407,
    "per_device_train_batch_size": 1,
    "gradient_accumulation_steps": 8,
    "warmup_steps": 5,
    "max_steps": 60,
    "learning_rate": 2e-4,
    "logging_steps": 1,
    "optim": "adamw_8bit",
    "weight_decay": 0.01,
    "lr_scheduler_type": "linear",
    "seed": 3407,
    "output_dir": str(BASE_DIR / "outputs"),
}

# ===== Identidade do Chatbot =====
USER_NAME = "voce"
ASSISTANT_NAME = "sophia"

# ===== Roteamento por keyword =====
KEYWORD_TO_FILE = {
    # stack / tecnologias
    "stack": "stack.md",
    "tecnologia": "stack.md", "tecnologias": "stack.md",
    "linguagem": "stack.md", "linguagens": "stack.md",
    "framework": "stack.md", "frameworks": "stack.md",
    "ferramenta": "stack.md", "ferramentas": "stack.md",
    "tech": "stack.md",

    # servicos (com typos)
    "servicos": "servicos.md", "serviços": "servicos.md",
    "servico": "servicos.md", "serviço": "servicos.md",
    "servicoes": "servicos.md", "serviçoes": "servicos.md",
    "serviçoes": "servicos.md", "servicoss": "servicos.md",
    "oque faz": "servicos.md", "o que faz": "servicos.md",
    "faz o que": "servicos.md", "faz oque": "servicos.md",

    # experiencia
    "experiencia": "experiencia.md", "experiência": "experiencia.md",
    "experiencias": "experiencia.md", "experiências": "experiencia.md",
    "projetos": "experiencia.md", "projeto": "experiencia.md",
    "portfolio": "experiencia.md", "portfólio": "experiencia.md",
    "carreira": "experiencia.md", "cv": "experiencia.md",

    # precos
    "precos": "precos.md", "preços": "precos.md",
    "preco": "precos.md", "preço": "precos.md",
    "valor": "precos.md", "valores": "precos.md",
    "orcamento": "precos.md", "orçamento": "precos.md",
    "cobra": "precos.md", "custa": "precos.md",

    # contato (com typos)
    "contato": "contato.md",
    "contatct": "contato.md", "conttato": "contato.md",
    "contatos": "contato.md",
    "email": "contato.md", "e-mail": "contato.md",
    "whatsapp": "contato.md", "whats": "contato.md",
    "telefone": "contato.md", "tel": "contato.md",
    "linkedin": "contato.md", "github": "contato.md",
    "falar": "contato.md", "chamar": "contato.md",

    # pessoal (com typos)
    "pessoal": "pessoal.md",
    "pessor": "pessoal.md", "pesoal": "pessoal.md",
    "sobre": "pessoal.md", "quem": "pessoal.md",
    "idade": "pessoal.md", "historia": "pessoal.md",
    "história": "pessoal.md", "trajetoria": "pessoal.md",
    "trajetória": "pessoal.md",
}

MENU_FILE = SKILLS_DIR / "index.md"

# ===== Saudações que disparam o menu =====
GREETINGS = {
    "oi", "ola", "olá", "eae", "e ai", "e aí", "opa", "fala",
    "bom dia", "boa tarde", "boa noite",
    "tudo bem", "tudo bom", "tudo certo",
    "hey", "hi", "hello",
    "start", "inicio", "início", "menu", "ajuda", "help",
}

# ===== System Prompt =====
def load_skills_context() -> str:
    """Carrega todos os .md de skills/, exceto index.md, para contexto geral."""
    parts = []
    if SKILLS_DIR.exists():
        for md_file in sorted(SKILLS_DIR.glob("*.md")):
            if md_file.name in {"index.md", "abordagem.md.bak"}:
                continue
            try:
                content = md_file.read_text(encoding="utf-8").strip()
                parts.append(f"### {md_file.stem.upper()}\n{content}")
            except Exception as e:
                print(f"[config] Erro lendo {md_file}: {e}")
    return "\n\n".join(parts)


SYSTEM_PROMPT = f"""Você é Sophia, assistente virtual do Alisson (uma IA).
Você NÃO é o Alisson. Quando falar dele, use SEMPRE "o Alisson" ou "ele".
NUNCA use "eu", "meu", "mim", "comigo" para se referir ao Alisson.

REGRAS DURAS:
- Responda em 1 a 3 frases. Só expanda se o usuário pedir detalhe.
- NUNCA liste conteúdo de arquivos internos nem diga "nos meus dados".
- NUNCA invente e-mail, telefone, link ou preço. Use EXATAMENTE o que está abaixo.
- NUNCA despeje contatos sem o usuário pedir.
- Fale como uma pessoa no WhatsApp: natural, direta, sem textão corporativo.

Use as informações abaixo APENAS quando o usuário perguntar algo relacionado:

{load_skills_context()}
"""