from datetime import datetime, timedelta
import os
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import pytest

from app.helpers import IMAGE_DIRECTORY
from app.utils import check_auth
from .main import app
client = TestClient(app)

# ---- test check_auth
@patch("app.utils.decode_jwt_token")
def test_check_auth_expired(mock_decode):
    mock_decode.return_value = {"user":1,"expire_at":(datetime.now()- timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")}
    mock_request = MagicMock()
    mock_request.headers = {"Authorization":"expired"}
    with pytest.raises(HTTPException) as exc_info:
        check_auth(mock_request)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Can't get the user because token is expired or wrong."

@patch("app.utils.decode_jwt_token")
def test_check_auth_valid(mock_decode):
    date = (datetime.now()+ timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
    mock_decode.return_value = {"user":1,"expire_at":date}
    mock_request = MagicMock()
    mock_request.headers = {"Authorization":"valid"}
    test = check_auth(mock_request)
    assert test["user"] == 1
    assert test["expire_at"] == date

@patch("app.utils.decode_jwt_token")
def test_check_auth_invalid(mock_decode):
    date = (datetime.now()+ timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
    mock_decode.return_value = {"user":1,"expire_at":date,"purpose":"invalid"}
    mock_request = MagicMock()
    mock_request.headers = {"Authorization":"invalid"}
    with pytest.raises(HTTPException) as exc_info:
        check_auth(mock_request)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Can't get the user because token is expired or wrong."

# ---- /project/projects Endpoint Tests ----

@patch("app.views_api.sqlconn")
def test_get_projects(mock_sqlconn):
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchall.side_effect = [
    [{'id': '639638dfa0b464bdc8fd81eb3e951d5f', 'creator': 'incurious', 'creator_id': 26, 'title': 'Wonderful',
    'created_at': datetime(2024, 10, 19, 18, 24, 30), 'likes': 122},
        {'id': 'a15d9c0583d560433464fbe84449a327', 'creator': 'test', 'creator_id': 28, 'title': 'Amazing Image',
        'created_at': datetime(2024, 10, 19, 18, 25, 22), 'likes': -523}]]
    response = client.get(f"/projects")
    assert response.status_code == 200
    assert response.json() == {'projects': [
        {
        'created_at': '2024-10-19T18:24:30',
        'creator': 'incurious',
        'creator_id': 26,
        'id': '639638dfa0b464bdc8fd81eb3e951d5f',
        'likes': 122,
        'title': 'Wonderful',
        },
        {
        'created_at': '2024-10-19T18:25:22',
        'creator': 'test',
        'creator_id': 28,
        'id': 'a15d9c0583d560433464fbe84449a327',
        'likes': -523,
        'title': 'Amazing Image',
        }]}

# ---- /project/project/{project_id} Endpoint Tests ----
@patch("app.views_api.os")
@patch("app.views_api.sqlconn")
def test_get_project_wo_jwt(mock_sqlconn,mock_os):
    project_id = "valid_project"
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {
        'content': 'This is an image',
        'created_at': '2024-10-19T18:24:30',
        'creator': 'incurious',
        'creator_id': 26,
        'likes': 0,
        'title': 'Wonderful'
        },
        {'l_d':None}
    ]
    mock_os.path.isfile.return_value = True
    mock_os.listdir.return_value = ['0_0_0.png', '1_1614_80.png', '2_250_1708.png', '3_247_550.png', '4_250_118.png', 'thumbnail.png']
    response = client.get(f"/project/project/{project_id}")
    assert response.status_code == 200
    assert response.json() == {
        'content': 'This is an image',
        'created_at': '2024-10-19T18:24:30',
        'creator': 'incurious',
        'creator_id': 26,
        'images': ['0_0_0.png','1_1614_80.png','2_250_1708.png','3_247_550.png','4_250_118.png'],
        'likes': 0,
        'title': 'Wonderful',
        'user_like': None
        }

@patch("app.views_api.os")
@patch("app.views_api.check_auth")
@patch("app.views_api.sqlconn")
def test_get_project_w_jwt(mock_sqlconn,mock_check_auth,mock_os):
    project_id = "valid_project"
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {
        'content': 'This is an image',
        'created_at': '2024-10-19T18:24:30',
        'creator': 'incurious',
        'creator_id': 26,
        'likes': 0,
        'title': 'Wonderful'
        },
        {'l_d': 'Like'}
    ]
    mock_os.path.isfile.return_value = True
    mock_os.listdir.return_value = ['0_0_0.png', '1_1614_80.png', '2_250_1708.png', '3_247_550.png', '4_250_118.png', 'thumbnail.png']
    response = client.get(f"/project/project/{project_id}")
    assert response.status_code == 200
    assert response.json() == {
        'content': 'This is an image',
        'created_at': '2024-10-19T18:24:30',
        'creator': 'incurious',
        'creator_id': 26,
        'images': ['0_0_0.png','1_1614_80.png','2_250_1708.png','3_247_550.png','4_250_118.png'],
        'likes': 0,
        'title': 'Wonderful',
        'user_like': "Like"
        }

# ---- /project/image/{project_id}/{filename} Endpoint Tests ----
@patch("app.views_api.os.path.exists")
@patch("app.views_api.FileResponse")
def test_get_image(mock_file_response, mock_exists):
    project_id = "valid_project"
    filename = "image.png"
    mock_exists.return_value = True 

    mock_file_response.return_value = MagicMock(status_code=200)

    response = client.get(f"/image/{project_id}/{filename}")
    assert response.status_code == 200
    mock_file_response.assert_called_once_with(os.path.join(IMAGE_DIRECTORY, project_id, filename)) 

@patch("app.views_api.os.path.exists")
@patch("app.views_api.FileResponse")
def test_get_image_not_found(mock_file_response, mock_exists):
    project_id = "valid_project"
    filename = "non_existent_image.png"
    mock_exists.return_value = False 

    response = client.get(f"/image/{project_id}/{filename}")

    assert response.status_code == 404 
    assert response.json() == {"detail": "Image not found."}
    mock_file_response.assert_not_called()


# ---- /project POST Endpoint Tests ----


@patch("app.views_api.os.path.exists")
@patch("app.views_api.psd_check") 
@patch("app.views_api.check_auth")
@patch("app.views_api.sqlconn") 
@patch("app.views_api.save_file")  
def test_check_and_save_psd_file(mock_save_file, mock_sqlconn, mock_check_auth, mock_psd_check, mock_exists):
    file_content = b"fake_psd_content"
    mock_title = "My Project"
    mock_content = "This is a project content description."

    mock_check_auth.return_value = {"user": 1}

    mock_psd_check.return_value = True

    mock_exists.return_value = False

    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.return_value = {"username": "Test-Artist"}

    mock_file = MagicMock()
    mock_file.read.return_value = file_content

    response = client.post(
        "/project/project",
        files={"file": ("test.psd", file_content, "application/psd")},
        data={"title": mock_title, "content": mock_content},
    )

    assert response.status_code == 200
    assert response.json() == {"msg": "PSD saved successfully!"}

    mock_sql_instance.session.add.assert_called_once()
    mock_sql_instance.session.commit.assert_called_once()

@patch("app.views_api.os.path.exists")
@patch("app.views_api.psd_check")
@patch("app.views_api.check_auth")
def test_check_and_save_psd_file_no_file(mock_check_auth, mock_psd_check, mock_exists):
    mock_check_auth.return_value = {"user": 1}
    mock_psd_check.return_value = False

    mock_exists.return_value = False

    response = client.post(
        "/project/project",
        files={"file": ("None.psd", "", "application/psd")},
        data={"title": "No File Test", "content": "Content without file"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "No file received."}

@patch("app.views_api.os.path.exists")
@patch("app.views_api.psd_check")
@patch("app.views_api.check_auth") 
def test_check_and_save_psd_file_invalid_psd(mock_check_auth, mock_psd_check, mock_exists):
    file_content = b"invalid_file_content"

    mock_check_auth.return_value = {"user": 1}
    mock_psd_check.return_value = False 

    mock_exists.return_value = False

    response = client.post(
        "/project/project",
        files={"file": ("invalid_file.psd", file_content, "application/psd")},
        data={"title": "Invalid PSD", "content": "This is invalid content."},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Sent file is not a psd."}
