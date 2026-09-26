#!/usr/bin/env python3
"""Build a browser-searchable index from the country repositories in README.md."""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
COUNTRY = re.compile(r'^\|[^|]*?\[([^\]]+)\]\(https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+)/?\)', re.I)
HEADING = re.compile(r'^#{2,4}\s+(.+?)\s*#*\s*$')
LINK = re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)', re.I)
BULLET = re.compile(r'^\s*[-*]\s+')
CATEGORIES = {
    'open data portals': 'Open Data portals',
    'legal entities': 'Legal Entities',
    'maps': 'Cadastral and other Maps',
    'cadastral and other maps': 'Cadastral and other Maps',
    'vehicles': 'Vehicles',
    'people': 'People, phones, social etc.',
    'people phones social etc': 'People, phones, social etc.',
    'public procurement': 'Public procurements',
    'public procurements': 'Public procurements',
    'whois': 'WHOIS',
}


def clean(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return re.sub(r'\s+', ' ', text.replace('**', '').replace('__', '').strip(' |\t—–-:.;'))


def countries_from_index(markdown):
    countries = []
    seen = set()
    for line in markdown.splitlines():
        match = COUNTRY.match(line)
        if not match:
            continue
        name, owner, repo = match.groups()
        key = (owner.lower(), repo.lower())
        if key not in seen:
            countries.append({'name': clean(name), 'owner': owner, 'repo': repo})
            seen.add(key)
    return countries


def resources_from_readme(markdown, country, repo_url):
    resources = []
    category = None
    subsection = ''
    seen = set()
    in_code = False
    for line in markdown.splitlines():
        if re.match(r'^\s*(```|~~~)', line):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading = HEADING.match(line)
        if heading:
            level = len(line) - len(line.lstrip('#'))
            label = clean(heading.group(1)).lower().rstrip(':')
            if level == 2:
                category = CATEGORIES.get(label)
                subsection = ''
            elif category == 'Vehicles' and level == 3:
                subsection = clean(heading.group(1))
            continue
        if not category or not (BULLET.match(line) or line.startswith('|')):
            continue
        match = LINK.search(line)
        if not match:
            continue
        name, url = match.groups()
        url = url.rstrip('.,;')
        if urlparse(url).scheme not in ('http', 'https'):
            continue
        name = clean(name)
        if not name or (category, url) in seen:
            continue
        seen.add((category, url))
        description = clean(line[match.end():])[:500]
        resources.append({
            'country': country,
            'category': category,
            'subsection': subsection,
            'name': name,
            'description': description,
            'url': url,
            'source': repo_url + '/blob/HEAD/README.md',
        })
    return resources


def fetch_readme(owner, repo):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{owner}/{repo}/readme',
        headers={
            'Accept': 'application/vnd.github.raw+json',
            'User-Agent': 'osint-countries-search-builder',
            **({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN']} if os.environ.get('GITHUB_TOKEN') else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode('utf-8-sig')


def build(output):
    index = (ROOT / 'README.md').read_text(encoding='utf-8')
    countries = countries_from_index(index)
    if not countries:
        raise RuntimeError('No country repositories found in the index README')
    records = []
    status = []
    for item in countries:
        repo_url = f"https://github.com/{item['owner']}/{item['repo']}"
        try:
            markdown = fetch_readme(item['owner'], item['repo'])
            found = resources_from_readme(markdown, item['name'], repo_url)
            if not found:
                raise ValueError('No resources recognized in README')
            records.extend(found)
            status.append({'country': item['name'], 'repository': repo_url, 'count': len(found), 'ok': True})
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"WARNING: {repo_url}: {exc}", file=sys.stderr)
            status.append({'country': item['name'], 'repository': repo_url, 'count': 0, 'ok': False})
    if not records:
        raise RuntimeError('No resources collected; refusing to publish an empty index')
    data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'countries': status,
        'resources': sorted(records, key=lambda r: (r['country'].casefold(), r['category'], r['name'].casefold())),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f"Indexed {len(records)} resources from {sum(c['ok'] for c in status)}/{len(status)} countries -> {output}")


if __name__ == '__main__':
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'site' / 'resources.json')
