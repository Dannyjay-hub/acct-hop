import glob, json, os, subprocess, sys, tempfile, time, unittest

SYNC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sync.py")


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def read(path):
    with open(path) as f:
        return f.read()


def put(root, acct, org, sid, title="t", age=60, valid=True, content=None):
    d = os.path.join(root, acct, org)
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "local_%s.json" % sid)
    with open(p, "w") as f:
        f.write(content if content is not None else json.dumps(
            {"sessionId": "local_" + sid, "cwd": "/x", "title": title,
             "createdAt": 1, "lastActivityAt": 2} if valid else {"nope": 1}))
    t = time.time() - age
    os.utime(p, (t, t))
    return p


class T(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "claude-code-sessions")
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_sync(self, *args, **extra_env):
        env = dict(os.environ, CSS_ROOT=self.root, CSS_HOME=self.home, **extra_env)
        return subprocess.run([sys.executable, SYNC, *args], env=env, capture_output=True, text=True).stdout

    def live(self, acct, org):
        return sorted(os.path.basename(f) for f in glob.glob(os.path.join(self.root, acct, org, "local_*.json")))

    def test_copies_sessions_across_accounts(self):
        put(self.root, "A", "o1", "aaa")
        put(self.root, "B", "o2", "bbb")
        self.run_sync()
        self.assertEqual(self.live("A", "o1"), ["local_aaa.json", "local_bbb.json"])
        self.assertEqual(self.live("B", "o2"), ["local_aaa.json", "local_bbb.json"])

    def test_newest_copy_wins(self):
        put(self.root, "A", "o1", "aaa", title="old", age=500)
        p = put(self.root, "B", "o2", "aaa", title="new", age=100)
        self.run_sync()
        self.assertEqual(json.loads(read(os.path.join(self.root, "A", "o1", "local_aaa.json")))["title"], "new")

    def test_deletion_marker_propagates_and_backs_up(self):
        put(self.root, "A", "o1", "aaa")
        put(self.root, "B", "o2", "aaa")
        write(os.path.join(self.root, "A", "o1", "deleted_aaa"), "123")
        self.run_sync()
        self.assertEqual(self.live("A", "o1"), [])
        self.assertEqual(self.live("B", "o2"), [])
        self.assertTrue(os.path.exists(os.path.join(self.root, "B", "o2", "deleted_aaa")))
        # one backup per account that still held the entry
        self.assertEqual(len(glob.glob(os.path.join(self.home, "trash", "*", "*"))), 2)

    def test_dry_run_writes_nothing(self):
        put(self.root, "A", "o1", "aaa")
        put(self.root, "B", "o2", "bbb")
        out = self.run_sync("--dry-run")
        self.assertIn("[dry-run] copy", out)
        self.assertEqual(self.live("A", "o1"), ["local_aaa.json"])
        self.assertFalse(os.path.exists(self.home))

    def test_unrecognised_layout_changes_nothing(self):
        os.makedirs(os.path.join(self.root, "A", "o1"))
        write(os.path.join(self.root, "A", "o1", "something.dat"), "x")
        out = self.run_sync()
        self.assertIn("status: unrecognised-layout", out)
        self.assertEqual(os.listdir(os.path.join(self.root, "A", "o1")), ["something.dat"])
        self.assertFalse(os.path.exists(self.home))

    def test_missing_folder_is_safe(self):
        os.rmdir(self.root)
        self.assertIn("status: unrecognised-layout", self.run_sync())

    def test_idempotent(self):
        put(self.root, "A", "o1", "aaa")
        put(self.root, "B", "o2", "bbb")
        self.run_sync()
        self.assertIn("0 copied", self.run_sync())

    def test_skips_corrupt_wrong_shape_and_in_progress_files(self):
        put(self.root, "A", "o1", "good")
        put(self.root, "A", "o1", "corrupt", content="{ not json")
        put(self.root, "A", "o1", "shape", valid=False)
        put(self.root, "A", "o1", "fresh", age=0)             # modified just now: may still be written
        put(self.root, "B", "o2", "bbb")
        out = self.run_sync()
        self.assertEqual(self.live("B", "o2"), ["local_bbb.json", "local_good.json"])
        self.assertIn("skipped 3", out)

    def test_initial_backup_made_once(self):
        put(self.root, "A", "o1", "aaa")
        put(self.root, "B", "o2", "bbb")
        self.run_sync()
        self.run_sync()
        self.assertEqual(len(glob.glob(os.path.join(self.home, "backups", "initial-*"))), 1)

    def test_other_files_in_org_folder_untouched(self):
        put(self.root, "A", "o1", "aaa")
        put(self.root, "B", "o2", "bbb")
        keep = os.path.join(self.root, "A", "o1", "scheduled-tasks.json")
        write(keep, "mine")
        self.run_sync()
        self.assertEqual(read(keep), "mine")
        self.assertFalse(os.path.exists(os.path.join(self.root, "B", "o2", "scheduled-tasks.json")))

    def test_non_english_characters_under_an_ascii_locale(self):
        """A GUI-launched app has no locale: Python then reads text as ASCII. Real session files contain
        non-English characters (accents, dashes, emoji) and must still sync."""
        body = json.dumps({"sessionId": "local_uni", "cwd": "/x", "title": "Caf\u00e9 \u2014 \u2713 \u00fcber \U0001f680",
                           "createdAt": 1, "lastActivityAt": 2}, ensure_ascii=False)
        p = put(self.root, "A", "o1", "uni", content=None)
        with open(p, "w", encoding="utf-8") as f:
            f.write(body)
        t = time.time() - 60
        os.utime(p, (t, t))
        put(self.root, "B", "o2", "bbb")
        ascii_env = dict(LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0")
        out = self.run_sync(**ascii_env)
        self.assertEqual(self.live("B", "o2"), ["local_bbb.json", "local_uni.json"], out)
        self.assertNotIn("skipped", out)
        with open(os.path.join(self.root, "B", "o2", "local_uni.json"), encoding="utf-8") as f:
            self.assertIn("\u2713", f.read())                    # copied byte for byte
        self.assertIn("layout recognised: yes", self.run_sync("doctor", **ascii_env))

    def test_doctor_is_redacted(self):
        put(self.root, "SECRET-ACCOUNT-ID", "SECRET-ORG-ID", "aaa", title="Private project name")
        out = self.run_sync("doctor")
        for secret in ("SECRET-ACCOUNT-ID", "SECRET-ORG-ID", "Private project name", self.tmp.name):
            self.assertNotIn(secret, out)
        self.assertIn("acct1", out)
        self.assertIn("layout recognised: yes", out)


if __name__ == "__main__":
    unittest.main()
