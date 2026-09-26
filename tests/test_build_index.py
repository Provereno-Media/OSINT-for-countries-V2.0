import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import build_index
from build_index import countries_from_index, resources_from_readme


class ParserTests(unittest.TestCase):
    def test_country_table_uses_first_cell_only(self):
        markdown = '| 🇰🇿 [Kazakhstan](https://github.com/paulpogoda/OSINT-Tools-Kazakhstan) | [Fork](https://github.com/other/fork) | ✅ Active |\n'
        self.assertEqual(countries_from_index(markdown), [{'name': 'Kazakhstan', 'owner': 'paulpogoda', 'repo': 'OSINT-Tools-Kazakhstan'}])

    def test_cuba_and_bulgaria_tree_links(self):
        markdown = '''| 🇧🇬 [Bulgaria](https://github.com/paulpogoda/OSINT-Tools-Bulgaria/tree/main) | @paulpogoda | Active |
| 🇨🇺 [Cuba](https://github.com/paulpogoda/osint-tools-cuba/tree/main) | @paulpogoda | Active |
'''
        self.assertEqual(
            [(item['name'], item['repo']) for item in countries_from_index(markdown)],
            [('Bulgaria', 'OSINT-Tools-Bulgaria'), ('Cuba', 'osint-tools-cuba')],
        )

    def test_categories_and_vehicle_subsection(self):
        markdown = '''## Table of contents
- [Registry](https://example.org/navigation)
## Legal Entities
- **[Company Registry](https://example.org/companies)** — Official registry
## Vehicles
### Land Vehicles
- [VIN Decoder](https://example.org/vin) - Search by VIN
## Legal Disclaimer
- [Policy](https://example.org/policy)
'''
        rows = resources_from_readme(markdown, 'Kazakhstan', 'https://github.com/example/repo')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['category'], 'Legal Entities')
        self.assertEqual(rows[1]['subsection'], 'Land Vehicles')

    def test_cuba_category_punctuation_and_icon(self):
        markdown = '''## People, Phones, Social etc.
- [Directory](https://example.org/people) - People search
## 🌐 WHOIS
- [NIC.cu](https://example.org/whois) - Domain information
'''
        rows = resources_from_readme(markdown, 'Cuba', 'https://github.com/paulpogoda/osint-tools-cuba')
        self.assertEqual([row['category'] for row in rows], ['People, phones, social etc.', 'WHOIS'])

    def test_kazakhstan_procurement_linked_heading(self):
        markdown = '''## Public procurement
### [Public procurement portal](https://goszakup.gov.kz/)
The public procurement portal is a state information system.
## WHOIS
- [Domain lookup](https://example.org/whois) - Lookup
'''
        rows = resources_from_readme(markdown, 'Kazakhstan', 'https://github.com/example/repo')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['category'], 'Public procurements')
        self.assertEqual(rows[0]['url'], 'https://goszakup.gov.kz/')
        self.assertIn('state information system', rows[0]['description'])

    def test_unrecognized_resource_link_is_reported(self):
        markdown = '''## Maps
Official resource: [Map](https://example.org/map)
## Other registries
- [Registry](https://example.org/registry)
'''
        candidates = []
        rows = resources_from_readme(markdown, 'Example', 'https://github.com/example/repo', candidates)
        self.assertEqual(rows, [])
        self.assertEqual([c['reason'] for c in candidates], ['unsupported_format', 'unrecognized_section'])
        self.assertEqual([c['line'] for c in candidates], [2, 4])

    def test_build_reads_canonical_repo_and_writes_report(self):
        index = '| [Example](https://github.com/example/OSINT-Tools-Example) | author | Active |\n'
        country = '## Maps\n- [Map](https://example.org/map) - Official map\n'
        def fake_readme(owner, repo):
            if (owner, repo) == (build_index.INDEX_OWNER, build_index.INDEX_REPO):
                return index
            self.assertEqual((owner, repo), ('example', 'OSINT-Tools-Example'))
            return country
        with tempfile.TemporaryDirectory() as folder, patch.object(build_index, 'fetch_readme', side_effect=fake_readme):
            output = Path(folder) / 'site' / 'resources.json'
            build_index.build(output)
            data = json.loads(output.read_text(encoding='utf-8'))
            report = json.loads(output.with_name('import-report.json').read_text(encoding='utf-8'))
        self.assertEqual(data['countries'][0]['categories']['Cadastral and other Maps'], 1)
        self.assertEqual(report['country_imported'], 1)
        self.assertEqual(report['resource_total'], 1)
        self.assertEqual(report['possible_omissions'], [])


if __name__ == '__main__':
    unittest.main()
