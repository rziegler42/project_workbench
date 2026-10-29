"""The git identity an approval records (``2026-10-29-approvals-name-the-approver-by-git-identity``)."""

import os
import stat
import tempfile
import time
import unittest
import unicodedata
import unittest.mock

from workbench import identity

REAL_GIT = next((path for path in identity.GIT_LOCATIONS if os.path.isfile(path) and os.access(path, os.X_OK)), None)
NAME = "Example Approver"
EMAIL = "12345+example@users.noreply.github.com"


def write(path, text, mode=0o644):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.chmod(path, mode)


class Parsing(unittest.TestCase):
    """`parse`: the stored text `Name <email>` back to an identity, under the same grammar."""

    def test_a_stored_text_round_trips(self):
        found = identity.check(NAME, EMAIL)
        self.assertEqual(found, identity.parse(found.text))

    def test_text_that_is_not_name_and_email_is_refused(self):
        for text in ("", "bob", "bob <>", "<a@b.c>", "Name a@b.c", "Name <a@b.c", "Name <a@b.c> ", "Name <a@b.c>x",
                     "Name <a b@c.d>", "Name <a@b.c><d@e.f>", "A <B> <a@b.c>", 5, None):
            with self.subTest(text=text):
                with self.assertRaises(identity.IdentityError):
                    identity.parse(text)

    def test_text_that_would_change_under_normalization_is_refused(self):
        with self.assertRaises(identity.IdentityError):
            identity.parse("José <%s>" % EMAIL)

    def test_the_name_rules_apply_on_parsing(self):
        for text in (" Name <%s>" % EMAIL, "ㅤ <%s>" % EMAIL, "a\nb <%s>" % EMAIL):
            with self.subTest(text=repr(text)):
                with self.assertRaises(identity.IdentityError):
                    identity.parse(text)


class Grammar(unittest.TestCase):
    def test_a_valid_identity_is_stored_as_name_and_email(self):
        found = identity.check(NAME, EMAIL)
        self.assertEqual(found.text, "%s <%s>" % (NAME, EMAIL))
        self.assertEqual((found.name, found.email), (NAME, EMAIL))

    def test_records_compare_by_the_lowercase_email(self):
        self.assertEqual(identity.check("A", "Mixed.Case@Example.COM").key, "mixed.case@example.com")
        self.assertEqual(identity.check("A", "x@y.z").key, identity.check("B", "X@Y.Z").key)

    def test_the_length_edges(self):
        identity.check("n", "a@b")
        identity.check("n" * 100, "a" * 49 + "@" + "b" * 50)
        for name, email in (("", EMAIL), ("n" * 101, EMAIL), (NAME, "a@"), (NAME, "@b"), (NAME, "ab"),
                            (NAME, "a" * 50 + "@" + "b" * 50), (NAME, "")):
            with self.subTest(name=name[:12], email=email[:12]):
                with self.assertRaises(identity.IdentityError):
                    identity.check(name, email)

    def test_the_stored_text_is_at_most_210_characters(self):
        found = identity.check("n" * 100, "a" * 49 + "@" + "b" * 50)
        self.assertLessEqual(len(found.text), 210)

    def test_angle_brackets_are_refused_in_either_part(self):
        for name, email in (("A <b>", EMAIL), ("A>", EMAIL), (NAME, "a<@b.c"), (NAME, "a@b>.c")):
            with self.subTest(name=name, email=email):
                with self.assertRaises(identity.IdentityError):
                    identity.check(name, email)

    def test_the_email_needs_exactly_one_at_sign(self):
        for email in ("nobody", "a@b@c", "@@@"):
            with self.subTest(email=email):
                with self.assertRaises(identity.IdentityError):
                    identity.check(NAME, email)

    def test_the_email_holds_only_printable_ascii(self):
        for email in ("a b@c.d", "a\tb@c.d", "a\nb@c.d", "a\x00b@c.d", "a\x7f@c.d", "é@c.d", "a@c​.d"):
            with self.subTest(email=email):
                with self.assertRaises(identity.IdentityError):
                    identity.check(NAME, email)

    def test_the_name_refuses_controls_formats_separators_and_unassigned(self):
        for bad in ("a\nb", "a\tb", "a\x1bb", "a​b", "a‮b", "a b", "a b", "a\ud800b", "ab",
                    "a͸b", "a\x7fb"):
            with self.subTest(name=repr(bad)):
                with self.assertRaises(identity.IdentityError):
                    identity.check(bad, EMAIL)

    def test_a_name_of_nothing_visible_is_refused(self):
        with self.assertRaises(identity.IdentityError):
            identity.check("   ", EMAIL)

    def test_a_name_that_prints_as_nothing_is_refused(self):
        for bad in ("ㅤ", "ᅟᅠ", "ﾠ", "⠀", "឴឵", "͏", "́̂", "⠀ㅤ ",
                    "ㅤ" * 5):
            with self.subTest(name=repr(bad)):
                with self.assertRaises(identity.IdentityError) as seen:
                    identity.check(bad, EMAIL)
                self.assertIn("git config --global user.name", str(seen.exception))

    def test_a_name_with_one_visible_character_is_kept(self):
        for good in ("A", "é", "黎", "7", "-", "☃", "ㅤA", "Aㅤ"):
            with self.subTest(name=repr(good)):
                self.assertEqual(identity.check(good, EMAIL).name, good)

    def test_a_name_with_a_blank_at_either_end_is_refused(self):
        for bad in (" Name", "Name ", " Name ", " Name", "Name ", "　Name"):
            with self.subTest(name=repr(bad)):
                with self.assertRaises(identity.IdentityError):
                    identity.check(bad, EMAIL)

    def test_a_name_with_inner_blanks_is_kept(self):
        self.assertEqual(identity.check("Mary  Ann Smith", EMAIL).name, "Mary  Ann Smith")

    def test_the_name_is_stored_normalized(self):
        decomposed = "José"
        found = identity.check(decomposed, EMAIL)
        self.assertEqual(found.name, unicodedata.normalize("NFC", decomposed))
        self.assertEqual(found.name, "José")

    def test_the_length_is_taken_after_normalization(self):
        identity.check("é" * 100, EMAIL)
        with self.assertRaises(identity.IdentityError):
            identity.check("é" * 101, EMAIL)

    def test_a_refusal_names_the_rule_and_how_to_set_the_value(self):
        with self.assertRaises(identity.IdentityError) as seen:
            identity.check(NAME, "nobody")
        text = str(seen.exception)
        self.assertIn("git config --global user.email", text)
        self.assertIn("@", text)


@unittest.skipUnless(REAL_GIT, "no git at a fixed location")
class Reading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.home = os.path.join(self.base, "home")
        os.makedirs(self.home)
        self.config = os.path.join(self.home, ".gitconfig")
        write(self.config, "[user]\n\tname = %s\n\temail = %s\n" % (NAME, EMAIL))

    def test_the_global_identity_is_read(self):
        self.assertEqual(identity.read(home=self.home).text, "%s <%s>" % (NAME, EMAIL))

    def test_a_missing_name_or_email_refuses_and_says_how_to_set_it(self):
        for body, command in (("[user]\n\temail = %s\n" % EMAIL, "user.name"), ("[user]\n\tname = %s\n" % NAME, "user.email"),
                              ("", "user.name")):
            with self.subTest(command=command):
                write(self.config, body)
                with self.assertRaises(identity.IdentityError) as seen:
                    identity.read(home=self.home)
                self.assertIn("git config --global %s" % command, str(seen.exception))

    def test_an_identity_outside_the_grammar_refuses(self):
        write(self.config, "[user]\n\tname = %s\n\temail = not-an-email\n" % NAME)
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    def test_the_project_git_config_is_never_read(self):
        project = os.path.join(self.base, "project")
        os.makedirs(os.path.join(project, ".git"))
        write(os.path.join(project, ".git", "config"), "[user]\n\tname = Evil\n\temail = evil@example.com\n")
        write(os.path.join(project, ".gitconfig"), "[user]\n\tname = Evil\n\temail = evil@example.com\n")
        here = os.getcwd()
        os.chdir(project)
        self.addCleanup(os.chdir, here)
        self.assertEqual(identity.read(home=self.home).text, "%s <%s>" % (NAME, EMAIL))

    def test_the_callers_git_variables_are_ignored(self):
        other = os.path.join(self.base, "other")
        write(other, "[user]\n\tname = Evil\n\temail = evil@example.com\n")
        hostile = {"GIT_CONFIG_GLOBAL": other, "GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "user.name",
                   "GIT_CONFIG_VALUE_0": "Evil", "GIT_CONFIG_KEY_1": "user.email", "GIT_CONFIG_VALUE_1": "evil@example.com",
                   "GIT_CONFIG_PARAMETERS": "'user.name=Evil' 'user.email=evil@example.com'",
                   "GIT_DIR": os.path.join(self.base, "nowhere"), "XDG_CONFIG_HOME": self.base,
                   "GIT_AUTHOR_NAME": "Evil", "GIT_CONFIG_SYSTEM": other}
        with unittest.mock.patch.dict(os.environ, hostile):
            self.assertEqual(identity.read(home=self.home).text, "%s <%s>" % (NAME, EMAIL))

    def test_an_include_directive_is_not_followed(self):
        included = os.path.join(self.base, "included")
        write(included, "[user]\n\tname = Included\n\temail = included@example.com\n")
        write(self.config, "[include]\n\tpath = %s\n" % included)
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    def test_a_git_earlier_on_the_callers_path_is_not_run(self):
        fake_dir = os.path.join(self.base, "fakebin")
        os.makedirs(fake_dir)
        write(os.path.join(fake_dir, "git"), "#!/bin/sh\necho Evil\n", 0o755)
        with unittest.mock.patch.dict(os.environ, {"PATH": fake_dir + os.pathsep + os.environ.get("PATH", "")}):
            self.assertEqual(identity.read(home=self.home).text, "%s <%s>" % (NAME, EMAIL))

    def test_a_global_file_that_is_a_symbolic_link_is_refused(self):
        real = os.path.join(self.base, "real-config")
        os.replace(self.config, real)
        os.symlink(real, self.config)
        with self.assertRaises(identity.IdentityError) as seen:
            identity.read(home=self.home)
        self.assertIn("symbolic link", str(seen.exception))

    def test_the_xdg_global_file_as_a_symbolic_link_is_refused_too(self):
        os.makedirs(os.path.join(self.home, ".config", "git"))
        real = os.path.join(self.base, "real-xdg")
        write(real, "[user]\n\tname = %s\n\temail = %s\n" % (NAME, EMAIL))
        os.symlink(real, os.path.join(self.home, ".config", "git", "config"))
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    @unittest.skipIf(os.geteuid() == 0, "root reads any file")
    def test_an_unreadable_global_file_is_refused(self):
        os.chmod(self.config, 0)
        self.addCleanup(os.chmod, self.config, stat.S_IRUSR | stat.S_IWUSR)
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    def test_a_global_file_that_is_a_directory_is_not_reported_as_a_missing_value(self):
        os.remove(self.config)
        os.makedirs(self.config)
        with self.assertRaises(identity.IdentityError) as seen:
            identity.read(home=self.home)
        self.assertNotIn("has no", str(seen.exception))

    def test_no_git_at_the_fixed_locations_refuses(self):
        with unittest.mock.patch.object(identity, "GIT_LOCATIONS", (os.path.join(self.base, "absent"),)):
            with self.assertRaises(identity.IdentityError) as seen:
                identity.read(home=self.home)
        self.assertIn("git", str(seen.exception))


class Invocation(unittest.TestCase):
    """What is run: the exact argument list, the working directory and the environment, seen by a stand-in git."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.home = os.path.join(self.base, "home")
        os.makedirs(self.home)
        self.log = os.path.join(self.base, "calls")
        self.fake = os.path.join(self.base, "git")

    def stand_in(self, body):
        write(self.fake, "#!/bin/sh\n" + body, 0o755)
        patcher = unittest.mock.patch.object(identity, "GIT_LOCATIONS", (self.fake,))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_two_runs_with_these_arguments_this_directory_and_this_environment(self):
        self.stand_in('{ echo "ARGS:$*"; echo "CWD:$(pwd -P)"; env | sort; } >> "%s"\n'
                      'case "$*" in *user.name) echo "%s";; *) echo "%s";; esac\n' % (self.log, NAME, EMAIL))
        hostile = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_DIR": "/nowhere", "SSH_AUTH_SOCK": "x", "EDITOR": "vi"}
        with unittest.mock.patch.dict(os.environ, hostile):
            identity.read(home=self.home)
        with open(self.log, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual([line for line in text.splitlines() if line.startswith("ARGS:")],
                         ["ARGS:config --global --get user.name", "ARGS:config --global --get user.email"])
        self.assertEqual({line for line in text.splitlines() if line.startswith("CWD:")}, {"CWD:" + self.home})
        names = {line.split("=", 1)[0] for line in text.splitlines() if "=" in line and not line.startswith(("ARGS", "CWD"))}
        # Exactly what the plan names, plus the variables a shell itself adds to its own environment.
        self.assertEqual(names - {"PWD", "SHLVL", "_", "OLDPWD"}, {"HOME", "PATH", "GIT_CONFIG_NOSYSTEM", "LC_ALL"})
        self.assertIn("GIT_CONFIG_NOSYSTEM=1", text)
        self.assertIn("LC_ALL=C", text)
        self.assertIn("HOME=" + self.home, text)
        self.assertIn("PATH=" + identity.FIXED_PATH, text)
        self.assertEqual(identity.FIXED_PATH, "/usr/bin:/bin:/usr/sbin:/sbin")

    def test_output_beyond_the_bound_is_refused(self):
        self.stand_in("head -c 100000 /dev/zero | tr '\\0' a\n")
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    def test_endless_output_is_stopped_at_the_bound_and_not_at_the_timeout(self):
        self.stand_in("yes aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")
        began = time.monotonic()
        with unittest.mock.patch.object(identity, "TIMEOUT", 8):
            with self.assertRaises(identity.IdentityError) as seen:
                identity.read(home=self.home)
        self.assertLess(time.monotonic() - began, 4)
        self.assertIn("longer than", str(seen.exception))

    def test_endless_error_output_is_stopped_too(self):
        self.stand_in("yes bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb >&2\n")
        began = time.monotonic()
        with unittest.mock.patch.object(identity, "TIMEOUT", 8):
            with self.assertRaises(identity.IdentityError):
                identity.read(home=self.home)
        self.assertLess(time.monotonic() - began, 4)

    def test_exit_one_with_no_message_is_a_missing_value(self):
        self.stand_in("exit 1\n")
        with self.assertRaises(identity.IdentityError) as seen:
            identity.read(home=self.home)
        self.assertIn("has no user.name", str(seen.exception))

    def test_exit_one_with_a_message_is_not_reported_as_missing(self):
        self.stand_in("echo 'fatal: the file is bad' >&2\nexit 1\n")
        with self.assertRaises(identity.IdentityError) as seen:
            identity.read(home=self.home)
        self.assertIn("could not read user.name", str(seen.exception))
        self.assertNotIn("has no", str(seen.exception))
        self.assertIn("fatal: the file is bad", str(seen.exception))

    def test_the_message_shown_from_git_is_escaped_and_short(self):
        self.stand_in("printf 'bad \\033[31m%s\\n' \"$(head -c 500 /dev/zero | tr '\\0' z)\" >&2\nexit 1\n")
        with self.assertRaises(identity.IdentityError) as seen:
            identity.read(home=self.home)
        self.assertNotIn("\x1b", str(seen.exception))
        self.assertLess(len(str(seen.exception)), 400)

    def test_a_run_that_does_not_end_is_stopped(self):
        self.stand_in("sleep 30\n")
        with unittest.mock.patch.object(identity, "TIMEOUT", 0.5):
            with self.assertRaises(identity.IdentityError) as seen:
                identity.read(home=self.home)
        self.assertIn("did not finish", str(seen.exception))

    def test_a_failing_git_refuses(self):
        self.stand_in("echo broken >&2\nexit 128\n")
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    def test_output_that_is_not_utf8_refuses(self):
        self.stand_in("printf '\\377\\376\\n'\n")
        with self.assertRaises(identity.IdentityError):
            identity.read(home=self.home)

    def test_account_home_is_the_one_in_the_account_database_not_the_environment(self):
        entry = unittest.mock.Mock(pw_dir=self.home)
        with unittest.mock.patch.object(identity.pwd, "getpwuid", return_value=entry):
            with unittest.mock.patch.dict(os.environ, {"HOME": "/elsewhere"}):
                self.assertEqual(identity.account_home(), self.home)

    def test_account_home_refuses_a_missing_entry_and_an_unusable_directory(self):
        with unittest.mock.patch.object(identity.pwd, "getpwuid", side_effect=KeyError(0)):
            with self.assertRaises(identity.IdentityError):
                identity.account_home()
        for bad in ("", "relative/dir", os.path.join(self.base, "absent")):
            with self.subTest(home=bad):
                with unittest.mock.patch.object(identity.pwd, "getpwuid", return_value=unittest.mock.Mock(pw_dir=bad)):
                    with self.assertRaises(identity.IdentityError):
                        identity.account_home()

    def test_the_home_comes_from_the_account_database_when_not_given(self):
        self.stand_in('echo "$HOME" >> "%s"\ncase "$*" in *user.name) echo "%s";; *) echo "%s";; esac\n'
                      % (self.log, NAME, EMAIL))
        with unittest.mock.patch.object(identity, "account_home", lambda: self.home):
            with unittest.mock.patch.dict(os.environ, {"HOME": "/elsewhere"}):
                identity.read()
        with open(self.log, encoding="utf-8") as handle:
            self.assertEqual(set(handle.read().split()), {self.home})


if __name__ == "__main__":
    unittest.main()
