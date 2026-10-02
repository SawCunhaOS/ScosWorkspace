"""Filtros de linha compartilhados pelos subcomandos."""


def contem(valor, termo):
    """Substring sem diferenciar maiusculas; termo vazio casa tudo."""
    return not termo or termo.lower() in (valor or "").lower()
