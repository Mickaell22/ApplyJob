"""Descubrimiento de ofertas laborales desde tableros de trabajo.

Antes era el modulo monolitico src/boards.py (~1600 lineas). Ahora es un
paquete: la API publica es IDENTICA -> `from src import boards; boards.discover_x()`
sigue funcionando. Los submodulos agrupan boards por naturaleza y _common
tiene lo compartido (headers, filtros geo/junior, helpers HTTP).
"""

from ._common import *        # noqa: F401,F403
from .remote_global import *  # noqa: F401,F403
from .linkedin import *       # noqa: F401,F403
from .local import *          # noqa: F401,F403
from .apply_urls import *     # noqa: F401,F403
