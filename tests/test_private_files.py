import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from put_esys.cli import app
from put_esys.models.files import PrivateFileItem, PrivateFilesList
from put_esys.services.ekursy.private_files import PrivateFilesService

SAMPLE_HTML = """
<html>
<body>
    <form action="https://ekursy.put.poznan.pl/user/files.php" method="post" id="mform1">
        <input type="hidden" name="sesskey" value="test_sesskey_123" />
        <input type="hidden" name="_qf__core_user_form_private_files" value="1" />
        <input type="hidden" name="files_filemanager" value="999888777" />
    </form>
    <script>
        M.form_filemanager.init(Y, {"context":{"id": 2222840}});
    </script>
</body>
</html>
"""

SAMPLE_LIST_RESPONSE = {
    "path": [{"name": "Pliki", "path": "/"}],
    "itemid": 999888777,
    "list": [
        {
            "filename": "assignment.py",
            "filepath": "/",
            "fullname": "assignment.py",
            "size": 1990,
            "filesize": "1.9 KB",
            "type": "file",
            "url": "https://ekursy.put.poznan.pl/draftfile.php/2222840/user/draft/999888777/assignment.py",
            "datemodified": 1699969969,
            "datecreated": 1699969966,
        },
        {
            "filename": "labs",
            "filepath": "/",
            "fullname": "labs",
            "size": 0,
            "filesize": "0 B",
            "type": "folder",
        },
    ],
}

SAMPLE_SUBDIR_RESPONSE = {
    "path": [{"name": "labs", "path": "/labs/"}],
    "itemid": 999888777,
    "list": [
        {
            "filename": "lab1.py",
            "filepath": "/labs/",
            "fullname": "lab1.py",
            "size": 512,
            "filesize": "512 B",
            "type": "file",
            "url": "https://ekursy.put.poznan.pl/draftfile.php/2222840/user/draft/999888777/lab1.py",
        }
    ],
}


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


def test_get_session_context(mock_session):
    resp_mock = MagicMock()
    resp_mock.text = SAMPLE_HTML
    resp_mock.status_code = 200
    mock_session.get.return_value = resp_mock

    service = PrivateFilesService(mock_session)
    ctx = service._get_session_context()

    assert ctx.sesskey == "test_sesskey_123"
    assert ctx.itemid == "999888777"
    assert ctx.ctx_id == "2222840"
    assert ctx.post_url == "https://ekursy.put.poznan.pl/user/files.php"


def test_list_files_flat(mock_session):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    resp_ajax = MagicMock(status_code=200)
    resp_ajax.json.return_value = SAMPLE_LIST_RESPONSE
    mock_session.post.return_value = resp_ajax

    service = PrivateFilesService(mock_session)
    result = service.list_files(path="/", recursive=False)

    assert isinstance(result, PrivateFilesList)
    assert result.file_count == 1
    assert result.folder_count == 1
    assert result.total_size == 1990
    assert len(result.items) == 2


def test_list_files_recursive(mock_session):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    def mock_post(url, data=None, **kwargs):
        resp = MagicMock(status_code=200)
        if data.get("filepath") == "/":
            resp.json.return_value = SAMPLE_LIST_RESPONSE
        elif data.get("filepath") == "/labs/":
            resp.json.return_value = SAMPLE_SUBDIR_RESPONSE
        return resp

    mock_session.post.side_effect = mock_post

    service = PrivateFilesService(mock_session)
    result = service.list_files(path="/", recursive=True)

    assert result.file_count == 2
    assert result.folder_count == 1
    assert any(i.filename == "lab1.py" for i in result.items)


def test_download_file(mock_session, tmp_path):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    resp_ajax = MagicMock(status_code=200)
    resp_ajax.json.return_value = SAMPLE_LIST_RESPONSE

    file_content_resp = MagicMock(status_code=200)
    file_content_resp.iter_content.return_value = [b"print('hello world')"]

    mock_session.get.side_effect = [resp_html, file_content_resp]
    mock_session.post.return_value = resp_ajax

    service = PrivateFilesService(mock_session)
    dest = tmp_path / "downloaded_assignment.py"

    saved = service.download_file("assignment.py", output_path=str(dest))
    assert saved == str(dest)
    assert dest.read_bytes() == b"print('hello world')"


def test_upload_file(mock_session, tmp_path):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    resp_upload = MagicMock(status_code=200, text="{}")
    resp_commit = MagicMock(status_code=200, text="OK")
    mock_session.post.side_effect = [resp_upload, resp_commit]

    test_file = tmp_path / "notes.txt"
    test_file.write_text("my notes", encoding="utf-8")

    service = PrivateFilesService(mock_session)
    uploaded = service.upload_file(str(test_file), remote_path="/")

    assert isinstance(uploaded, PrivateFileItem)
    assert uploaded.filename == "notes.txt"
    assert uploaded.size == len("my notes")


def test_create_folder(mock_session):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    resp_mkdir = MagicMock(status_code=200)
    resp_mkdir.json.return_value = {"filepath": "/my_folder/"}
    resp_commit = MagicMock(status_code=200, text="OK")
    mock_session.post.side_effect = [resp_mkdir, resp_commit]

    service = PrivateFilesService(mock_session)
    assert service.create_folder("my_folder", parent_path="/") is True


def test_rename_file(mock_session):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    resp_rename = MagicMock(status_code=200)
    resp_rename.json.return_value = {"result": True}
    resp_commit = MagicMock(status_code=200, text="OK")
    mock_session.post.side_effect = [resp_rename, resp_commit]

    service = PrivateFilesService(mock_session)
    assert service.rename_file("old.txt", "new.txt", path="/") is True


def test_move_file(mock_session):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    resp_move = MagicMock(status_code=200)
    resp_move.json.return_value = {"result": True}
    resp_commit = MagicMock(status_code=200, text="OK")
    mock_session.post.side_effect = [resp_move, resp_commit]

    service = PrivateFilesService(mock_session)
    assert service.move_file("doc.txt", target_path="/archive/", source_path="/") is True


def test_delete_file(mock_session):
    resp_html = MagicMock(text=SAMPLE_HTML, status_code=200)
    mock_session.get.return_value = resp_html

    resp_del = MagicMock(status_code=200)
    resp_del.json.return_value = {"result": True}
    resp_commit = MagicMock(status_code=200, text="OK")
    mock_session.post.side_effect = [resp_del, resp_commit]

    service = PrivateFilesService(mock_session)
    assert service.delete_file("old.txt", path="/") is True


# CLI tests
runner = CliRunner()


@patch("put_esys.cli.files.check_authenticated")
@patch("put_esys.cli.files.EKursyClient")
def test_cli_files_list_json(mock_ekursy, mock_check_auth):
    mock_service = MagicMock()
    mock_service.list_files.return_value = PrivateFilesList(
        path="/",
        items=[
            PrivateFileItem(
                filename="data.csv",
                filepath="/",
                fullname="data.csv",
                size=120,
                filesize="120 B",
                type="file",
            )
        ],
        file_count=1,
        folder_count=0,
        total_size=120,
    )
    with patch("put_esys.cli.files.PrivateFilesService", return_value=mock_service):
        result = runner.invoke(app, ["files", "list", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["file_count"] == 1
        assert parsed["items"][0]["filename"] == "data.csv"


@patch("put_esys.cli.files.check_authenticated")
@patch("put_esys.cli.files.EKursyClient")
def test_cli_files_mkdir_non_interactive(mock_ekursy, mock_check_auth):
    mock_service = MagicMock()
    mock_service.create_folder.return_value = True

    with patch("put_esys.cli.files.PrivateFilesService", return_value=mock_service):
        result = runner.invoke(app, ["files", "mkdir", "testdir", "--yes"])
        assert result.exit_code == 0
        assert "Folder created successfully" in result.output
        mock_service.create_folder.assert_called_once_with("testdir", parent_path="/")


@patch("put_esys.cli.files.check_authenticated")
@patch("put_esys.cli.files.EKursyClient")
def test_cli_files_delete_non_interactive(mock_ekursy, mock_check_auth):
    mock_service = MagicMock()
    mock_service.delete_file.return_value = True

    with patch("put_esys.cli.files.PrivateFilesService", return_value=mock_service):
        result = runner.invoke(app, ["files", "delete", "test.txt", "--yes"])
        assert result.exit_code == 0
        assert "Deleted successfully" in result.output
        mock_service.delete_file.assert_called_once_with("test.txt", path="/")
