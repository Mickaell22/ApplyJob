"""Persistencia simple de URLs vistas/postuladas (txt, una URL por linea).

Compartido por run_discover.py (descubrir/listar) y gen_cover.py (generar carta),
para no duplicar la logica de tracking.

- applied_urls.txt          : URLs con carta generada o postulacion real -> nunca re-listar.
- output/seen_discovered.txt : URLs ya mostradas en una corrida de descubrimiento
  previa -> evita re-listar lo mismo cada dia (output/ esta gitignored).

ponytail: txt plano en vez de DB. Techo: O(n) al cargar y sin locking. Para
miles de URLs/dia migrar a sqlite; a esta escala (decenas/dia) sobra.
"""
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLIED_FILE = os.path.join(_BASE, "applied_urls.txt")
SEEN_FILE = os.path.join(_BASE, "output", "seen_discovered.txt")


def _load(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}


def _append(path: str, url: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def load_applied() -> set[str]:
    return _load(APPLIED_FILE)


def mark_applied(url: str) -> None:
    _append(APPLIED_FILE, url)


def load_seen() -> set[str]:
    return _load(SEEN_FILE)


def mark_seen(url: str) -> None:
    _append(SEEN_FILE, url)


# Self-check minimo (sin frameworks): correr `python3 src/applied.py`
if __name__ == "__main__":
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "applied_selfcheck.txt")
    if os.path.exists(tmp):
        os.remove(tmp)
    assert _load(tmp) == set(), "archivo inexistente debe dar set vacio"
    _append(tmp, "https://a.com/1")
    _append(tmp, "https://a.com/2")
    assert _load(tmp) == {"https://a.com/1", "https://a.com/2"}, "deben persistir 2 urls"
    os.remove(tmp)
    print("applied.py self-check OK")
