"""The sealed state: the key and the rollback mark in the guarded store, the seal, atomic writes and the lock
(checklist items 10 and 12 of `docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment C."""

import fcntl
import json
import os
import stat
import unittest

import support_review
from support_review import NAMESPACE, OTHER_PLAN, PLAN, SPEC, key_of
from workbench.wbkit import safefs


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


class Key(support_review.Review):
    def test_the_key_is_made_once_at_first_use_with_mode_0600_in_directories_of_mode_0700(self):
        self.assertFalse(os.path.exists(self.store_path()))
        self.document("init", PLAN)
        self.assertEqual(32, len(self.key()))
        self.assertEqual(0o600, mode(self.store_path("seal-key")))
        for folder in (self.store_path(), self.store_path("marks")):
            self.assertEqual(0o700, mode(folder), folder)

    def test_a_second_review_uses_the_same_key(self):
        self.document("init", PLAN)
        first = self.key()
        self.document("init", OTHER_PLAN)
        self.assertEqual(first, self.key())

    def test_status_never_makes_a_key(self):
        self.document("init", PLAN)
        os.unlink(self.store_path("seal-key"))
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])
        self.assertFalse(os.path.exists(self.store_path("seal-key")))

    def test_a_key_of_the_wrong_length_is_never_replaced(self):
        self.document("init", PLAN)
        with open(self.store_path("seal-key"), "wb") as handle:
            handle.write(b"short")
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])
        self.refused("init", OTHER_PLAN, contains="seal key")
        with open(self.store_path("seal-key"), "rb") as handle:
            self.assertEqual(b"short", handle.read())

    def test_a_key_that_is_a_link_is_refused_and_not_followed(self):
        self.document("init", PLAN)
        real = self.key()
        os.unlink(self.store_path("seal-key"))
        with open(os.path.join(self.base, "stolen-key"), "wb") as handle:
            handle.write(real)
        os.symlink(os.path.join(self.base, "stolen-key"), self.store_path("seal-key"))
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])
        self.refused("init", OTHER_PLAN, contains="seal key")

    def test_a_store_that_is_missing_is_refused_and_named(self):
        os.rename(self.store, self.store + "-moved")
        self.refused("init", PLAN, contains="guarded store")
        self.assertFalse(os.path.exists(self.path(self.review_dir("plan", PLAN))))


class Seal(support_review.Review):
    def setUp(self):
        super().setUp()
        self.document("init", PLAN)

    def sealed_body(self):
        body = self.state()
        del body["seal"]
        return body

    def test_a_state_sealed_by_the_stored_key_is_read_as_sealed(self):
        got = self.document("status", PLAN)
        self.assertEqual(("ok", ""), (got["seal"], got["reason"]))

    def test_the_seal_is_the_hmac_of_the_canonical_json_of_every_other_field(self):
        import hashlib
        import hmac
        body = self.sealed_body()
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(hmac.new(self.key(), canonical, hashlib.sha256).hexdigest(), self.state()["seal"])

    def test_a_field_changed_by_hand_is_unsealed_whichever_field_it_is(self):
        original = self.read(self.state_rel("plan", PLAN))
        edits = (lambda s: s["window"].update(bound=5), lambda s: s.update(closed="2026-01-01T00:00:00Z"),
                 lambda s: s["rounds"].append({"n": 1}), lambda s: s["decisions"].append({"finding": "R1-F1"}),
                 lambda s: s.update(path=SPEC), lambda s: s.update(kind="spec"))
        for edit in edits:
            self.write(self.state_rel("plan", PLAN), original, binary=True)
            state = self.state()
            edit(state)
            self.write(self.state_rel("plan", PLAN), json.dumps(state))
            got = self.document("status", PLAN)
            self.assertEqual("unsealed", got["seal"])
            self.assertIn(got["reason"], ("the seal does not match", "the state is not usable"))

    def test_a_seal_made_with_another_key_is_unsealed(self):
        self.forge(self.sealed_body(), key=b"k" * 32)
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])

    def test_a_missing_or_malformed_seal_is_unsealed(self):
        body = self.sealed_body()
        for seal in (None, "", "0" * 63, "g" * 64, 5, ["a"]):
            state = dict(body)
            if seal is not None:
                state["seal"] = seal
            self.write(self.state_rel("plan", PLAN), json.dumps(state))
            self.assertEqual("unsealed", self.document("status", PLAN)["seal"], seal)

    def test_a_missing_key_is_unsealed_and_the_state_can_still_be_read(self):
        os.unlink(self.store_path("seal-key"))
        got = self.document("status", PLAN)
        self.assertEqual(("unsealed", "there is no seal key on this machine"), (got["seal"], got["reason"]))
        self.assertEqual("plan", got["kind"])

    def test_a_state_that_does_not_parse_as_the_documented_shape_is_unsealed_not_a_crash(self):
        body = self.sealed_body()
        bad = [b"", b"[]", b"7", b"not json", b"\xff\xfe", b'{"a": 1, "a": 2}', b'{"x": NaN}', b'{"x": 1.5}',
               b"[" * 40 + b"]" * 40, b'{"x": "\\ud800"}', b"x" * (self.helper.MAX_STATE + 1)]
        bad += [json.dumps(dict(body, extra=1)).encode(), json.dumps(dict(body, format=2)).encode(),
                json.dumps(dict(body, format=True)).encode(), json.dumps(dict(body, kind="code")).encode(),
                json.dumps(dict(body, window={"first": 1, "bound": 6})).encode(),
                json.dumps(dict(body, window={"first": 1, "bound": 0})).encode(),
                json.dumps(dict(body, window={"first": 2, "bound": 3})).encode(),
                json.dumps(dict(body, window={"first": True, "bound": 3})).encode(),
                json.dumps(dict(body, window={"first": 1})).encode(),
                json.dumps(dict(body, rounds={})).encode(), json.dumps(dict(body, rounds=[1])).encode(),
                json.dumps(dict(body, closed="yesterday")).encode(),
                json.dumps(dict(body, path="x" * 5000)).encode()]
        for data in bad:
            self.write(self.state_rel("plan", PLAN), data, binary=True)
            got = self.document("status", PLAN)
            self.assertEqual(("unsealed", "the state is not usable"), (got["seal"], got["reason"]), data[:60])

    def test_a_validly_sealed_state_with_a_control_character_or_a_huge_string_is_still_refused(self):
        for field, value in (("path", PLAN + "\x1b[31m"), ("closed", "2026-01-01T00:00:00Z\n")):
            self.forge(dict(self.sealed_body(), **{field: value}))
            self.assertEqual("unsealed", self.document("status", PLAN)["seal"], field)
        self.forge(dict(self.sealed_body(), rounds=[{"note": "x" * 5000}]))
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])

    def test_a_validly_sealed_state_of_another_document_is_unsealed(self):
        self.document("init", OTHER_PLAN)
        other = self.state("plan", OTHER_PLAN)
        self.write(self.state_rel("plan", PLAN), json.dumps(other))
        self.assertEqual("unsealed", self.document("status", PLAN)["seal"])

    def test_a_state_file_that_is_a_link_is_unsealed_and_not_followed(self):
        real = os.path.join(self.base, "real-state.json")
        os.rename(self.path(self.state_rel("plan", PLAN)), real)
        os.symlink(real, self.path(self.state_rel("plan", PLAN)))
        got = self.document("status", PLAN)
        self.assertEqual("unsealed", got["seal"])
        self.assertNotIn("rounds_total", got)


class Rollback(support_review.Review):
    """A seal detects change, not replay: an older state is still validly sealed, so a mark in the guarded store
    names the highest counts it has sealed."""

    def setUp(self):
        super().setUp()
        self.document("init", PLAN)
        self.name = key_of("plan", PLAN)
        self.older = self.read(self.state_rel("plan", PLAN))

    def newer(self, rounds, decisions=()):
        body = self.state()
        body["rounds"] = [{"n": n + 1} for n in range(rounds)]
        body["decisions"] = [{"finding": "R1-F%d" % n} for n in decisions]
        return self.forge(body)

    def test_the_mark_after_init_is_zero_rounds_and_zero_decisions(self):
        with open(self.store_path("marks", self.name)) as handle:
            self.assertEqual({"rounds": 0, "decisions": 0}, json.load(handle))

    def test_a_state_with_the_counts_of_the_mark_or_more_is_sealed(self):
        self.newer(2, [1])
        self.set_mark(self.name, 2, 1)
        self.assertEqual("ok", self.document("status", PLAN)["seal"])
        self.set_mark(self.name, 1, 0)
        self.assertEqual("ok", self.document("status", PLAN)["seal"])

    def test_an_older_sealed_state_below_the_mark_in_rounds_is_rolled_back(self):
        self.newer(2)
        self.set_mark(self.name, 2, 0)
        self.write(self.state_rel("plan", PLAN), self.older, binary=True)
        got = self.document("status", PLAN)
        self.assertEqual(("rolled_back", "the state is older than the last one sealed here"),
                         (got["seal"], got["reason"]))

    def test_an_older_sealed_state_below_the_mark_in_decisions_is_rolled_back(self):
        self.newer(1, [1, 2])
        self.set_mark(self.name, 1, 2)
        self.newer(1, [1])
        self.assertEqual("rolled_back", self.document("status", PLAN)["seal"])

    def test_reading_a_forged_state_does_not_raise_the_mark(self):
        self.newer(3)
        self.assertEqual("ok", self.document("status", PLAN)["seal"])
        with open(self.store_path("marks", self.name)) as handle:
            self.assertEqual({"rounds": 0, "decisions": 0}, json.load(handle))

    def test_a_mark_that_is_missing_means_nothing_was_sealed_beyond_the_state(self):
        os.unlink(self.store_path("marks", self.name))
        self.assertEqual("ok", self.document("status", PLAN)["seal"])

    def test_a_mark_that_is_not_usable_is_unsealed_not_a_crash(self):
        for text in ("", "[]", "7", "{", '{"rounds": 1}', '{"rounds": -1, "decisions": 0}',
                     '{"rounds": 1.5, "decisions": 0}', '{"rounds": true, "decisions": 0}',
                     '{"rounds": 0, "decisions": 0, "x": 1}', '{"rounds": 99999999999, "decisions": 0}'):
            with open(self.store_path("marks", self.name), "w") as handle:
                handle.write(text)
            got = self.document("status", PLAN)
            self.assertEqual(("unsealed", "the rollback mark is not usable"), (got["seal"], got["reason"]), text)

    def test_the_mark_is_kept_per_review(self):
        self.document("init", SPEC)
        self.assertEqual(sorted([self.name, key_of("spec", SPEC)]), sorted(os.listdir(self.store_path("marks"))))

    def test_saving_a_state_never_lowers_the_mark(self):
        self.set_mark(self.name, 4, 4)
        state = self.state()
        state["rounds"] = [{"n": 1}, {"n": 2}]
        self.helper.save(self.root, self.helper.Guarded(self.project_id), self.helper.resolve(self.root, PLAN), state)
        with open(self.store_path("marks", self.name)) as handle:
            self.assertEqual({"rounds": 4, "decisions": 4}, json.load(handle))

    def test_saving_a_state_raises_the_mark_to_its_counts(self):
        state = self.state()
        state["rounds"] = [{"n": 1}, {"n": 2}]
        state["decisions"] = [{"finding": "R1-F1"}]
        self.helper.save(self.root, self.helper.Guarded(self.project_id), self.helper.resolve(self.root, PLAN), state)
        with open(self.store_path("marks", self.name)) as handle:
            self.assertEqual({"rounds": 2, "decisions": 1}, json.load(handle))
        self.assertEqual("ok", self.document("status", PLAN)["seal"])


class Writes(support_review.Review):
    def test_init_writes_only_the_review_directory_and_the_stores_key_mark_and_lock(self):
        before_project, before_store = self.tree(self.root), self.tree(self.store)
        self.document("init", PLAN)
        directory = self.review_dir("plan", PLAN)
        root_changes = self.changed(before_project, self.tree(self.root))
        self.assertEqual(sorted([".workbench/workbench", ".workbench/workbench/review-engine", directory,
                                 directory + "/state.json", directory + "/ledger.md"]),
                         [name.replace(os.sep, "/") for name in root_changes])
        prefix = os.path.join("projects", self.project_id)
        self.assertEqual(sorted([prefix, os.path.join(prefix, "review-engine"),
                                 os.path.join(prefix, "review-engine", "seal-key"),
                                 os.path.join(prefix, "review-engine", "lock"),
                                 os.path.join(prefix, "review-engine", "marks"),
                                 os.path.join(prefix, "review-engine", "marks", key_of("plan", PLAN))]),
                         self.changed(before_store, self.tree(self.store)))

    def test_the_reviewed_document_is_not_touched(self):
        before = self.read(PLAN)
        mtime = os.stat(self.path(PLAN)).st_mtime_ns
        self.document("init", PLAN)
        self.assertEqual((before, mtime), (self.read(PLAN), os.stat(self.path(PLAN)).st_mtime_ns))

    def test_the_ledger_is_a_readable_rendering_and_is_never_read_back(self):
        self.document("init", PLAN)
        ledger = self.read(self.review_dir("plan", PLAN) + "/ledger.md").decode()
        self.assertIn(PLAN, ledger)
        self.assertIn("0 of 3 rounds", ledger)
        self.write(self.review_dir("plan", PLAN) + "/ledger.md", "tampered\n")
        self.assertEqual("ok", self.document("status", PLAN)["seal"])

    def test_a_write_that_fails_part_way_leaves_the_old_state_and_no_temporary_file(self):
        self.document("init", PLAN)
        before = self.read(self.state_rel("plan", PLAN))
        directory = self.path(self.review_dir("plan", PLAN))
        state = self.state()
        state["window"]["bound"] = 4
        loaded = self.helper.Guarded(self.project_id)

        def fail(stage, **info):
            if stage == "before_rename":
                raise OSError(5, "disk went away", info.get("rel"))

        safefs._hook = fail
        self.addCleanup(setattr, safefs, "_hook", None)
        with self.assertRaises(self.helper.Refused):
            self.helper.save(self.root, loaded, self.helper.resolve(self.root, PLAN), state)
        safefs._hook = None
        self.assertEqual(before, self.read(self.state_rel("plan", PLAN)))
        self.assertEqual(sorted(["state.json", "ledger.md"]), sorted(os.listdir(directory)))


class Lock(support_review.Review):
    def test_a_second_run_while_one_holds_the_lock_is_refused_and_writes_nothing(self):
        self.document("init", PLAN)
        before = (self.tree(self.root), self.tree(self.store))
        with open(self.store_path("lock"), "rb") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            self.refused("init", OTHER_PLAN, contains="lock")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))
        self.assertEqual("plan", self.document("init", OTHER_PLAN)["kind"])

    def test_a_lock_that_is_a_link_is_refused(self):
        self.document("init", PLAN)
        os.unlink(self.store_path("lock"))
        os.symlink(os.path.join(self.base, "somewhere"), self.store_path("lock"))
        self.refused("init", OTHER_PLAN)
        self.assertFalse(os.path.exists(os.path.join(self.base, "somewhere")))


if __name__ == "__main__":
    unittest.main()
