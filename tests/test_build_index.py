import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build_index import countries_from_index, resources_from_readme


class ParserTests(unittest.TestCase):
    def test_country_table_uses_first_cell_only(self):
        markdown = '| 🇰🇿 [Kazakhstan](https://github.com/paulpogoda/OSINT-Tools-Kazakhstan) | [Fork](https://github.com/other/fork) | ✅ Active |\n'
        self.assertEqual(countries_from_index(markdown), [{'name': 'Kazakhstan', 'owner': 'paulpogoda', 'repo': 'OSINT-Tools-Kazakhstan'}])

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
        self.assertEqual(rows[1]['name'], 'VIN Decoder')

    def test_kazakhstan_procurement_linked_heading(self):
        markdown = '''## Public procurement
### [Public procurement portal](https://goszakup.gov.kz/)
The public procurement portal is a state information system.
- registration of participants;
## WHOIS
- [Domain lookup](https://example.org/whois) - Lookup
'''
        rows = resources_from_readme(markdown, 'Kazakhstan', 'https://github.com/example/repo')
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['name'], 'Public procurement portal')
        self.assertEqual(rows[0]['category'], 'Public procurements')
        self.assertEqual(rows[0]['url'], 'https://goszakup.gov.kz/')
        self.assertIn('state information system', rows[0]['description'])
        self.assertEqual(rows[1]['category'], 'WHOIS')


if __name__ == '__main__':
    unittest.main()
