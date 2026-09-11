"""board_config.local(): the local app's database path, read from the "local" block of board.config.json."""
import io, json, os, sys, unittest

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(HERE, 'exporters'))
import board_config  # noqa: E402


class Local(unittest.TestCase):
    def test_default_path(self):
        self.assertEqual(board_config.local({}), {'databasePath': 'out/local/board.db'})
        self.assertEqual(board_config.local({'local': {}}), {'databasePath': 'out/local/board.db'})

    def test_a_given_path_is_kept_and_tilde_expanded(self):
        self.assertEqual(board_config.local({'local': {'databasePath': 'D:/data/board.db'}}),
                         {'databasePath': 'D:/data/board.db'})
        got = board_config.local({'local': {'databasePath': '~/board/board.db'}})['databasePath']
        self.assertEqual(got, os.path.expanduser('~/board/board.db'))
        self.assertFalse(got.startswith('~'))

    def test_a_block_that_is_not_an_object_raises_naming_local(self):
        for block in (['x'], 'out/x.db', 3, None):
            with self.subTest(block=block), self.assertRaises(ValueError) as cm:
                board_config.local({'local': block})
            self.assertIn('"local" must be an object', str(cm.exception))

    def test_a_path_that_is_not_a_non_empty_string_raises_naming_the_key(self):
        for value in (3, None, ['a'], '', '   '):
            with self.subTest(value=value), self.assertRaises(ValueError) as cm:
                board_config.local({'local': {'databasePath': value}})
            self.assertIn('local.databasePath must be a non-empty string', str(cm.exception))

    def test_other_keys_of_the_block_are_left_alone(self):
        self.assertEqual(board_config.local({'local': {'databasePath': 'a.db', 'port': 8080}}), {'databasePath': 'a.db'})

    def test_repo_config_holds_the_key(self):
        with io.open(os.path.join(HERE, 'board.config.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        self.assertEqual(cfg['local'], {'databasePath': 'out/local/board.db'})
        self.assertEqual(board_config.local(cfg), {'databasePath': 'out/local/board.db'})


if __name__ == '__main__':
    unittest.main()
