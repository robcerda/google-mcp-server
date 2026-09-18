"""Tests for shared drive ("Team Drive") support in the Drive client.

Two layers here:

1. Behavioural tests that drive the real client with a mocked Drive service and
   assert on the request it builds - parent resolution and the shared drive
   flags actually sent.
2. A static audit that every Drive API call in drive_client.py passes
   supportsAllDrives when the API accepts it. Shared drive support is
   per-call-site, so a single new call that forgets the flag silently breaks
   shared drives while personal Drive keeps working. The audit catches that at
   the point it is introduced rather than in production.
"""

import ast
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from google_mcp_server.drive_client import GoogleDriveClient

DRIVE_CLIENT_SOURCE = Path(__file__).parent.parent / "src" / "google_mcp_server" / "drive_client.py"

# googleapiclient exposes the media variants under names the discovery
# document does not use.
METHOD_ALIASES = {"export_media": "export", "get_media": "get"}


@pytest.fixture
def client():
    """A Drive client whose underlying service is a mock."""
    with patch("google_mcp_server.drive_client.build") as build:
        build.return_value = MagicMock()
        return GoogleDriveClient(credentials=MagicMock())


def executed_kwargs(mock_method):
    """The keyword arguments of the single call made to a mocked API method."""
    assert mock_method.call_count == 1, f"expected exactly one call, got {mock_method.call_count}"
    return mock_method.call_args.kwargs


class TestParentResolution:
    """Where a new file or folder is placed, per drive_id/parent_folder_id."""

    @pytest.mark.parametrize(
        "drive_id, parent_folder_id, expected_parents",
        [
            (None, None, None),                             # personal drive root
            (None, "folder123", ["folder123"]),              # personal drive folder
            ("shared_drive_123", None, ["shared_drive_123"]),  # shared drive root
            ("shared_drive_123", "folder456", ["folder456"]),  # folder in shared drive
        ],
    )
    def test_upload_file_parents(self, client, drive_id, parent_folder_id, expected_parents):
        client.upload_file(
            name="test_file.txt",
            content="hello",
            parent_folder_id=parent_folder_id or "",
            drive_id=drive_id or "",
        )
        body = executed_kwargs(client.service.files().create)["body"]
        assert body.get("parents") == expected_parents

    @pytest.mark.parametrize(
        "drive_id, parent_folder_id, expected_parents",
        [
            (None, None, None),
            (None, "folder123", ["folder123"]),
            ("shared_drive_123", None, ["shared_drive_123"]),
            ("shared_drive_123", "folder456", ["folder456"]),
        ],
    )
    def test_create_folder_parents(self, client, drive_id, parent_folder_id, expected_parents):
        client.create_folder(
            name="New Folder",
            parent_folder_id=parent_folder_id or "",
            drive_id=drive_id or "",
        )
        body = executed_kwargs(client.service.files().create)["body"]
        assert body.get("parents") == expected_parents


class TestSharedDriveFlags:
    """The flags that make a request visible to shared drives at all."""

    def test_list_files_requests_shared_drive_items(self, client):
        client.list_files()
        kwargs = executed_kwargs(client.service.files().list)
        assert kwargs["supportsAllDrives"] is True
        assert kwargs["includeItemsFromAllDrives"] is True

    def test_list_files_scopes_to_a_single_drive(self, client):
        client.list_files(drive_id="shared_drive_123")
        kwargs = executed_kwargs(client.service.files().list)
        assert kwargs["driveId"] == "shared_drive_123"
        assert kwargs["corpora"] == "drive"

    def test_get_file_metadata_supports_all_drives(self, client):
        client.get_file("file123")
        assert executed_kwargs(client.service.files().get)["supportsAllDrives"] is True

    def test_file_content_download_supports_all_drives(self, client):
        """Every content read goes through get_media, including the chunked,
        sample and search tools - so this one call site covers all of them."""
        client._get_file_content("file123", "text/plain")
        assert executed_kwargs(client.service.files().get_media)["supportsAllDrives"] is True

    def test_delete_file_supports_all_drives(self, client):
        client.service.files().get().execute.return_value = {"name": "doomed.txt"}
        client.delete_file("file123")
        # Both the pre-delete name lookup and the delete itself must carry it.
        assert client.service.files().get.call_args.kwargs["supportsAllDrives"] is True
        assert executed_kwargs(client.service.files().delete)["supportsAllDrives"] is True

    @pytest.mark.parametrize("drive_id", ["", "shared_drive_123"])
    def test_uploads_support_all_drives_either_way(self, client, drive_id):
        """The flag is unconditional - a shared drive folder can be passed as a
        bare parent_folder_id, with no drive_id to hint at it."""
        client.upload_file(name="f.txt", content="x", drive_id=drive_id)
        assert executed_kwargs(client.service.files().create)["supportsAllDrives"] is True


class TestEveryCallSiteSupportsAllDrives:
    """Static audit of drive_client.py against the Drive v3 discovery document."""

    @staticmethod
    def _discovery_parameters():
        """Which parameters each Drive v3 method accepts, per Google's own spec.

        Located through the installed package rather than by globbing: the
        document lives under .venv, and glob skips dotted directories, which
        would silently skip this test instead of running it.
        """
        import googleapiclient.discovery_cache

        path = Path(googleapiclient.discovery_cache.__file__).parent / "documents" / "drive.v3.json"
        if not path.exists():
            pytest.skip(f"Drive v3 discovery document not found at {path}")
        return json.loads(path.read_text())["resources"]

    @staticmethod
    def _api_calls():
        """Every self.service.<resource>().<method>(...) call in the module."""
        tree = ast.parse(DRIVE_CLIENT_SOURCE.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Call)
                and isinstance(func.value.func, ast.Attribute)
                and isinstance(func.value.func.value, ast.Attribute)
                and func.value.func.value.attr == "service"
            ):
                continue
            keywords = {kw.arg for kw in node.keywords}
            yield (
                node.lineno,
                func.value.func.attr,          # resource, e.g. "files"
                func.attr,                     # method, e.g. "get"
                "supportsAllDrives" in keywords,
                None in keywords,              # built from a **request_params dict
            )

    def test_found_the_call_sites(self):
        """Guard against the AST matcher silently matching nothing."""
        assert len(list(self._api_calls())) >= 20

    def test_no_call_site_omits_supports_all_drives(self):
        resources = self._discovery_parameters()
        missing = []

        for lineno, resource, method, has_flag, uses_kwargs in self._api_calls():
            real_method = METHOD_ALIASES.get(method, method)
            params = resources.get(resource, {}).get("methods", {}).get(real_method, {}).get("parameters", {})
            if "supportsAllDrives" not in params:
                continue  # e.g. files.export and the drives resource do not take it
            if has_flag or uses_kwargs:
                continue
            missing.append(f"drive_client.py:{lineno} {resource}.{method}()")

        assert not missing, (
            "Drive calls missing supportsAllDrives=True, which breaks shared "
            "drives:\n  " + "\n  ".join(missing)
        )
