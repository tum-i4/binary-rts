import unittest
from pathlib import Path

from binaryrts.vcs.base import Changelist, ChangelistItem, ChangelistItemAction
from binaryrts.vcs.git import temp_repo, temp_clone, GitClient


class GitClientTestCase(unittest.TestCase):
    def test_git_client(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                # set up git client
                client: GitClient = GitClient.from_repo(local_repo)

                # create and commit file
                first_file: Path = Path("new_file")
                first_file.touch()

                # make sure, that status is correct
                changelist = client.get_status()
                self.assertEqual(
                    changelist,
                    Changelist(
                        items=[
                            ChangelistItem(
                                filepath=first_file,
                                action=ChangelistItemAction.ADDED,
                            )
                        ]
                    ),
                )

                # stage changes
                client.git_repo.git.add(".")

                # make sure, that status is correct
                changelist = client.get_status()
                self.assertEqual(
                    changelist,
                    Changelist(
                        items=[
                            ChangelistItem(
                                filepath=first_file,
                                action=ChangelistItemAction.ADDED,
                            )
                        ]
                    ),
                )

                client.git_repo.git.commit(message="Commit 1")

                # make sure, that status is correct
                changelist = client.get_status()
                self.assertEqual(
                    changelist,
                    Changelist(items=[]),
                )

                client.git_repo.remote().push()

                # modify and commit changes
                first_file.write_text("new data")

                # make sure, that status is correct
                changelist = client.get_status()
                self.assertEqual(
                    changelist,
                    Changelist(
                        items=[
                            ChangelistItem(
                                filepath=first_file,
                                action=ChangelistItemAction.MODIFIED,
                            )
                        ]
                    ),
                )

                client.git_repo.git.add(".")

                changelist = client.get_status()
                self.assertEqual(
                    changelist,
                    Changelist(
                        items=[
                            ChangelistItem(
                                filepath=first_file,
                                action=ChangelistItemAction.MODIFIED,
                            )
                        ]
                    ),
                )

                # create another file and commit
                second_file: Path = Path("added_file")
                second_file.touch()

                client.git_repo.git.add(".")

                # make sure, that status is correct
                changelist = client.get_status()
                self.assertEqual(
                    changelist,
                    Changelist(
                        items=[
                            ChangelistItem(
                                filepath=first_file,
                                action=ChangelistItemAction.MODIFIED,
                            ),
                            ChangelistItem(
                                filepath=second_file,
                                action=ChangelistItemAction.ADDED,
                            ),
                        ]
                    ),
                )

                client.git_repo.git.commit(message="Commit 2")
                client.git_repo.remote().push()

                # set up expected changelist
                expected_changelist: Changelist = Changelist(
                    items=[
                        ChangelistItem(
                            filepath=first_file,
                            action=ChangelistItemAction.MODIFIED,
                        ),
                        ChangelistItem(
                            filepath=second_file,
                            action=ChangelistItemAction.ADDED,
                        ),
                    ]
                )

                # get changelist between last commit before HEAD (@~) and HEAD
                changelist: Changelist = client.get_diff(
                    from_revision="@~", to_revision="@"
                )

                self.assertEqual(changelist, expected_changelist)

    def test_get_file_content_at_commit(self):
        with temp_repo() as (remote_repo_path, remote_repo):
            with temp_clone() as (local_repo_path, local_repo):
                # set up git client
                client: GitClient = GitClient.from_repo(local_repo)

                # create and commit file
                first_file = Path("new_file.txt")
                first_file.write_text("Hello")

                client.git_repo.git.add(".")
                client.git_repo.git.commit(message="Commit 1")
                client.git_repo.remote().push()

                self.assertTrue(first_file.exists())
                self.assertEqual("Hello", first_file.read_text())
                first_file.unlink()
                self.assertFalse(first_file.exists())

                previous_file_content: str = client.get_file_content_at_revision(
                    revision="HEAD", filepath=first_file
                )
                self.assertEqual("Hello", previous_file_content)

                client.git_repo.git.add(".")
                client.git_repo.git.commit(message="Commit 2")

                self.assertFalse(first_file.exists())

                previous_file_content: str = client.get_file_content_at_revision(
                    revision="HEAD~1", filepath=first_file
                )
                self.assertEqual("Hello", previous_file_content)


if __name__ == "__main__":
    unittest.main()
