import sqlite3
import unittest

from ManagedEngine.backend import core, native_source, schema


class NativeSourceTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(core.SCHEMA)
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

    def test_conflicting_identity_update_is_retained_as_conflict(self):
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
        result = native_source.feeds(self.db, 'PUT', {
            'namespace': 'install-a', 'accountID': 'one', 'feedIDs': ['a', 'b'],
            'mediaType': 'paper', 'processingMode': 'important', 'threshold': 9,
        })
        self.assertEqual({item['feed_id'] for item in result['feeds']}, {'a', 'b'})
        self.assertEqual({item['processing_mode'] for item in result['feeds']}, {'important'})
        self.assertEqual({item['revision'] for item in result['feeds']}, {1})
        self.assertEqual(result['affectedSources'], [{'feedID': 'a', 'observationCount': 0}, {'feedID': 'b', 'observationCount': 0}])
        self.assertEqual(result['historicalRerun'], 'explicit-preview-required')
        with self.assertRaises(ValueError):
            native_source.feeds(self.db, 'PUT', {
                'namespace': 'install-a', 'accountID': 'one', 'feedID': 'a',
                'mediaType': 'paper', 'revision': 0,
            })

    def test_schema_pass_creates_native_tables_at_new_version(self):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        schema.ensure(db)
        self.assertIsNotNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='native_source_observations'").fetchone())
        self.assertEqual(schema.version(db), schema.SCHEMA_VERSION)
        db.close()


if __name__ == '__main__':
    unittest.main()
