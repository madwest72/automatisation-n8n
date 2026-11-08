"""Static publication checks. Does not execute workflows or contact services."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    r'(?:sk-[A-Za-z0-9_-]{16,}|(?:ntn_|secret_|ghp_|github_pat_|xox[baprs]-)[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{25,}|AKIA[A-Z0-9]{16}|ya29\.[A-Za-z0-9_.-]+)',
    r'(?i)Bearer\s+[A-Za-z0-9_.-]{10,}',
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',
    r'''(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[=:]\s*["']?[A-Za-z0-9_./+-]{12,}''',
]

def strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if re.fullmatch(r'(?i)authorization|password|secret|token|api.?key', key) and child:
                raise ValueError('Unexpected sensitive field: ' + key)
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, str):
        yield value

def check(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['active'] is False, 'Workflow must remain inactive in this template'
    assert not data.get('pinData'), 'Pinned execution data must not be published'
    assert not any(k in data for k in ('meta', 'id', 'versionId', 'staticData'))
    names = [node['name'] for node in data['nodes']]
    assert len(names) == len(set(names)), 'Duplicate node names'
    for node in data['nodes']:
        assert 'credentials' not in node, 'Credential association present'
        assert 'webhookId' not in node, 'Original webhook ID present'
    for source, groups in data['connections'].items():
        assert source in names, 'Unknown source node'
        for outputs in groups.values():
            for output in outputs:
                for edge in output:
                    assert edge['node'] in names, 'Unknown target node'
    for value in strings(data):
        assert not any(re.search(p, value) for p in PATTERNS), 'Potential secret detected; inspect locally without logging it'
    print(f'OK {path.name}: {len(names)} nodes; JSON, connections and secret-pattern checks passed')

if __name__ == '__main__':
    files = sorted((ROOT / 'workflows').glob('*.json'))
    assert len(files) == 2, 'Expected two workflow exports'
    for file in files:
        check(file)
