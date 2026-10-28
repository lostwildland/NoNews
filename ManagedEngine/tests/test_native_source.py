import sqlite3
import tempfile
import unittest
from pathlib import Path

from ManagedEngine.backend import core, native_source, schema
from ManagedEngine.backend.core import InformationDB


class NativeSourceTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(core.SCHEMA)
        self.db.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
        self.db.executescript(native_source.SCHEMA)

    def tearDown(self):
        self.db.close()

    def test_same_article_ids_in_two_accounts_stay_distinct(self):
        first = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Same article', 'mediaType': 'news', 'identityType': 'url',
            'identityValue': 'https://example.com/story?edition=one',
        })
        second = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'two', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Same article', 'mediaType': 'news', 'identityType': 'url',
            'identityValue': 'https://example.com/story?edition=one',
        })
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(first['item_id'], second['item_id'])
        self.assertEqual(len(native_source.list_observations(self.db, {})['observations']), 2)

    def test_unresolved_observation_is_readable_without_processing_identity(self):
        row = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Needs resolution',
        })
        self.assertEqual(row['identity_state'], 'unresolved')
        self.assertIsNone(row['item_id'])
        self.assertEqual(row['contexts'], [])

    def test_untyped_url_is_retained_as_unresolved_evidence(self):
        row = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Unconfigured', 'identityType': 'url', 'identityValue': 'https://example.com/story',
        })
        self.assertEqual(row['identity_state'], 'unresolved')
        self.assertIsNone(row['item_id'])
        self.assertEqual(row['identity_type'], 'url')
        self.assertEqual(row['raw_identity_value'], 'https://example.com/story')

        body = {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Story', 'mediaType': 'news', 'identityType': 'url',
            'identityValue': 'https://example.com/story',
        }
        original = native_source.observe(self.db, body)
        repeated = native_source.observe(self.db, {key: value for key, value in body.items() if key not in {'mediaType', 'identityType', 'identityValue'}})
        self.assertEqual(repeated['identity_state'], 'verified')
        self.assertEqual(repeated['item_id'], original['item_id'])
        self.assertEqual(len(repeated['identityEvidence']), 1)
        self.assertEqual(repeated['identityEvidence'][0]['raw_identity_value'], 'https://example.com/story')

    def test_ipv6_url_authority_remains_distinct(self):
        first = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'one',
            'mediaType': 'news', 'identityType': 'url', 'identityValue': 'https://[::1]:80/story',
        })
        second = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'two',
            'mediaType': 'news', 'identityType': 'url', 'identityValue': 'https://[::1:80]/story',
        })
        self.assertNotEqual(first['item_id'], second['item_id'])

        with self.assertRaises(ValueError):
            native_source.observe(self.db, {
                'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
                'title': 'Wrong media', 'mediaType': 'paper', 'identityType': 'video', 'identityValue': 'video-id-1',
            })

    def test_policy_is_pinned_into_new_processing_context(self):
        self.db.execute("INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?)", ('nonews.prompt.curator', '{"role":"curator"}', 'now'))
        native_source.feeds(self.db, 'PUT', {'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'title': 'Named feed', 'curatorPromptID': 'curator', 'threshold': 7})
        row = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Story', 'mediaType': 'news', 'identityType': 'url', 'identityValue': 'https://example.com/story',
        })
        self.assertEqual(row['contexts'][0]['curator_prompt_id'], 'curator')
        self.assertEqual(row['contexts'][0]['threshold'], 7.0)
        self.assertEqual(row['contexts'][0]['policy_revision'], 1)
        self.assertEqual(row['contexts'][0]['processing_mode'], 'disabled')

    def test_unsupported_identity_type_is_refused(self):
        with self.assertRaises(ValueError):
            native_source.observe(self.db, {
                'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
                'title': 'Story', 'mediaType': 'news', 'identityType': 'made-up', 'identityValue': 'anything',
            })

        original = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'First', 'mediaType': 'news', 'identityType': 'url',
            'identityValue': 'https://example.com/first',
        })
        changed = native_source.observe(self.db, {
            'namespace': 'install-a', 'accountID': 'one', 'feedID': 'feed', 'articleID': 'article',
            'title': 'Changed', 'mediaType': 'news', 'identityType': 'url',
            'identityValue': 'https://example.com/second',
        })
        self.assertEqual(changed['identity_state'], 'conflict')
        self.assertEqual(changed['item_id'], original['item_id'])

    def test_policy_batch_update_is_explicit_and_revisioned(self):
        self.db.execute("INSERT INTO app_settings(key,value,updated_at) VALUES (?,?,?)", ('nonews.prompt.curator', '{"role":"curator"}', 'now'))
        result = native_source.feeds(self.db, 'PUT', {
            'namespace': 'install-a', 'accountID': 'one', 'feedIDs': ['a', 'b'],
            'mediaType': 'paper', 'processingMode': 'important', 'curatorPromptID': 'curator', 'threshold': 9,
        })
        self.assertEqual({item['feed_id'] for item in result['feeds']}, {'a', 'b'})
        self.assertEqual({item['processing_mode'] for item in result['feeds']}, {'important'})
        self.assertEqual({item['revision'] for item in result['feeds']}, {1})
        self.assertEqual(result['affectedSources'], [{'feedID': 'a', 'sourceName': 'a', 'observationCount': 0}, {'feedID': 'b', 'sourceName': 'b', 'observationCount': 0}])
        self.assertEqual(result['historicalRerun'], 'explicit-preview-required')
        with self.assertRaises(ValueError):
            native_source.feeds(self.db, 'PUT', {
                'namespace': 'install-a', 'accountID': 'one', 'feedID': 'a',
                'mediaType': 'paper', 'revision': 0,
            })

    def test_schema_pass_migrates_populated_version_41_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'information.sqlite'
            db = sqlite3.connect(path)
            db.executescript(core.SCHEMA)
            schema.stamp(db, 41)
            db.execute("INSERT INTO feeds(id,freshrss_feed_id,title,first_seen_at,last_seen_at) VALUES ('f','f','Feed','now','now')")
            db.commit()
            db.close()
            with InformationDB(path) as migrated:
                self.assertEqual(schema.version(migrated.db), 46)
                self.assertIsNotNone(migrated.db.execute("SELECT 1 FROM sqlite_master WHERE name='native_source_observations'").fetchone())
                self.assertEqual(migrated.db.execute("SELECT title FROM feeds WHERE id='f'").fetchone()[0], 'Feed')

    def test_schema_pass_creates_native_tables_at_new_version(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        schema.ensure(db)
        self.assertIsNotNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='native_source_observations'").fetchone())
        self.assertEqual(schema.version(db), schema.SCHEMA_VERSION)
        db.close()


if __name__ == '__main__':
    unittest.main()
