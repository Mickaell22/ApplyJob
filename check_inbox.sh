#!/usr/bin/env bash
cd /home/mickaell/Escritorio/Proyectos\ MICKAELL/ApplyJob
source .venv/bin/activate
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from src import inbox
results = inbox.check_inbox(max_emails=20)
summary = inbox.summarize(results)
print(summary)

# Guardar resumen para consulta del agente
import json
from datetime import datetime, timezone
state = {
    'last_check': datetime.now(timezone.utc).isoformat(),
    'count': len(results),
    'summary': summary,
    'items': [{k: r.get(k) for k in ['subject','from','date']} for r in results[:5]]
}
with open('/tmp/applyjob-inbox-state.json', 'w') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
" 2>&1 >> /tmp/applyjob-inbox.log
