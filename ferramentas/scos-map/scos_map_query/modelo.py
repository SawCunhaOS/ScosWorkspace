"""Contrato entre leitura, consulta e saida (AD-2). Sem logica."""

from dataclasses import dataclass, field
from typing import Optional


class ErroConsulta(Exception):
    """Erro esperado: codigo de saida 2 (uso), 3 (ausente) ou 4 (schema)."""

    def __init__(self, codigo, mensagem, acao="-"):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.acao = acao


@dataclass
class Secao:
    nome: str
    colunas: list
    linhas: list  # conjunto completo que casa com os filtros
    total: int
    tipo: str = "dados"  # dados | resumo
    fonte: str = ""


@dataclass
class Resultado:
    secoes: list
    avisos: list = field(default_factory=list)
    limitacoes: list = field(default_factory=list)
    refinar: list = field(default_factory=list)


@dataclass
class Meta:
    """Envelope de um fato lido; campo que o fato nao tem fica None."""

    fato: str
    arquivo: str  # relativo a raiz do workspace, com "/"
    confianca: Optional[str] = None
    estado: Optional[str] = None
    completude: Optional[str] = None
    base: Optional[str] = None
    desvios: Optional[list] = None
    heads: dict = field(default_factory=dict)  # repo -> head gravado no mapa
    commits_desde: dict = field(default_factory=dict)  # repo -> N
    limitacoes: list = field(default_factory=list)
    motivo: Optional[str] = None
    schema_versao: Optional[str] = None
    gerado: Optional[str] = None
    avisos: list = field(default_factory=list)


@dataclass
class Opcoes:
    """Flags comuns de cli.py entregues ao render (AD-11); None = teto padrao."""

    limit: Optional[int] = None
    bytes: Optional[int] = None
    todos: bool = False
    base: bool = False


TETO_LINHAS = 50
TETO_BYTES = 6000
MAX_LINHA = 240
