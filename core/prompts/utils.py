"""
Utilitarios compartilhados do modulo de prompts.

Funcoes auxiliares para formatacao, validacao e manipulacao
de texto de prompts.
"""

import re


def limpar_prompt(texto: str) -> str:
    """
    Normaliza um texto de prompt.

    - Remove linhas em branco excessivas (maximo 2 consecutivas)
    - Strip de espacos no inicio/fim
    - Normaliza line endings para \\n
    """
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def truncar(texto: str, max_chars: int = 3000, sufixo: str = "\n[...truncado]") -> str:
    """Trunca texto respeitando limite de caracteres, adicionando sufixo."""
    if len(texto) <= max_chars:
        return texto
    return texto[:max_chars] + sufixo


def contar_tokens_estimado(texto: str, chars_por_token: int = 4) -> int:
    """Estimativa de tokens baseada em caracteres (1 token ~ 4 chars em portugues)."""
    return len(texto) // chars_por_token


def formatar_lista_secoes(nomes: list[str]) -> str:
    """Formata lista de nomes de secoes para log legivel."""
    return ", ".join(nomes) if nomes else "(vazio)"
