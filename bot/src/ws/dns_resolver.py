"""
Resolvedor DNS-over-HTTPS (DoH).

Objetivo: contornar bloqueio de DNS do provedor (comum em sites de aposta no
Brasil). Em vez de depender do DNS do sistema/roteador — que alguns provedores
adulteram para bloquear o dominio — resolvemos o IP via HTTPS direto na
Cloudflare (1.1.1.1) e no Google (8.8.8.8).

Conectamos pelos IPs literais (1.1.1.1 / 8.8.8.8), nao por nome, para evitar o
problema do "ovo e galinha" (precisar de DNS para achar o servidor de DNS).
Os certificados desses IPs sao validos (tem o IP no SAN), entao a verificacao
TLS continua ativa.

Tudo aqui e best-effort: se a resolucao DoH falhar, retornamos vazio e o
chamador segue com o comportamento normal (DNS do sistema). Nunca quebra o bot.
"""

import json
import logging
import ssl
import urllib.parse
import urllib.request
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Servidores DoH (endpoint -> headers da API JSON). Ordem = prioridade.
# Primeiro por hostname (o provedor bloqueia o dominio de aposta, nao o
# 'dns.google'/'cloudflare-dns.com', entao o DNS do sistema resolve esses
# nomes normalmente e o certificado TLS casa direitinho). Depois por IP
# literal, caso ate o nome do servidor DoH nao resolva.
DOH_SERVERS = [
    ("https://dns.google/resolve", {}),
    ("https://cloudflare-dns.com/dns-query",
     {"accept": "application/dns-json"}),
    ("https://8.8.8.8/resolve", {}),
    ("https://1.1.1.1/dns-query", {"accept": "application/dns-json"}),
]

_TIMEOUT = 4.0

# Cache simples por processo: host -> lista de IPs.
_cache: Dict[str, List[str]] = {}


def _query_doh(url_base: str, headers: Dict[str, str], host: str) -> List[str]:
    """Consulta um servidor DoH e retorna IPs A (IPv4)."""
    qs = urllib.parse.urlencode({"name": host, "type": "A"})
    url = f"{url_base}?{qs}"
    req = urllib.request.Request(url, headers=headers or {})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    ips: List[str] = []
    for ans in data.get("Answer", []):
        # type 1 = registro A (IPv4)
        if ans.get("type") == 1 and ans.get("data"):
            ips.append(ans["data"].strip())
    return ips


def resolve(host: str) -> List[str]:
    """Resolve um hostname para lista de IPv4 via DoH. [] se falhar tudo."""
    host = (host or "").strip().lower()
    if not host:
        return []
    if host in _cache:
        return _cache[host]

    for url_base, headers in DOH_SERVERS:
        try:
            ips = _query_doh(url_base, headers, host)
            if ips:
                logger.info("DoH %s -> %s (via %s)", host, ips, url_base)
                _cache[host] = ips
                return ips
        except Exception as e:
            logger.debug("DoH falhou em %s para %s: %s", url_base, host, e)
            continue

    logger.warning("DoH nao resolveu '%s' (todos os servidores falharam)", host)
    return []


def host_from_url(url: str) -> Optional[str]:
    """Extrai o hostname de uma URL."""
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc or urlparse(f"//{url}").netloc
        return (netloc.split(":")[0] or None) if netloc else None
    except Exception:
        return None


def build_host_resolver_rules(urls: List[str]) -> str:
    """Monta a string do flag --host-resolver-rules do Chrome.

    Para cada URL resolve o host (e tambem a variante com/sem 'www.') via DoH
    e gera entradas 'MAP host ip'. Retorna "" se nada foi resolvido — nesse
    caso o chamador simplesmente nao adiciona o flag.
    """
    rules: List[str] = []
    seen: set = set()

    for url in urls:
        host = host_from_url(url)
        if not host:
            continue

        # Resolve o host e tambem a variante apex/www (CDNs costumam separar).
        variants = {host}
        if host.startswith("www."):
            variants.add(host[4:])
        else:
            variants.add(f"www.{host}")

        for h in variants:
            if h in seen:
                continue
            seen.add(h)
            ips = resolve(h)
            if ips:
                # Usa o primeiro IP; mantemos o Host/SNI original, entao
                # CDNs (CloudFront/Vercel) roteiam corretamente.
                rules.append(f"MAP {h} {ips[0]}")

    return ",".join(rules)
