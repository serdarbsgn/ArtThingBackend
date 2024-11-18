from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from .main import app

client = TestClient(app)

# ---- /Userstats Endpoint Tests ----

def test_userstats_no_jwt():
    response = client.get("/userstats")
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

def test_userstats_wrong_jwt():
    jwt = "wrong_jwt"
    response = client.get("/userstats",headers={"Authorization":jwt})
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

@patch("app.views_user_api.check_auth")
def test_userstats_correct_jwt(mock_check_auth):
    jwt = "correct_jwt"
    mock_check_auth.return_value = {"user": -1}
    response = client.get("/userstats",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {'projectCommentCount': 0,
                               'projectCommentKarmaTotal': 0,
                               'projectCount': 0,
                               'projectKarmaTotal': 0}

# ---- /creator/{creatorName} Endpoint Tests ----

def test_creator_nonexistent_username():
    creator_name = "nonexistent"
    response = client.get(f"/creator/{creator_name}")
    assert response.status_code == 404
    assert response.json() == {"detail":"Creator doesn't exist."}

@patch("app.views_user_api.sqlconn")
def test_creator_existing_username(mock_sqlconn):
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {"creator_id": 123, "profile_picture": "mock_pic.jpg", "join_date": datetime(2024, 10, 16, 14, 43, 8)},  
        {"count": 5},
        {"sum": None}
    ]
    creator_name = "existing_user"
    response = client.get(f"/creator/{creator_name}")
    assert response.status_code == 200
    assert response.json() == {'creatorProfilePicture': 'mock_pic.jpg',
                               'joinDate': '2024-10-16T14:43:08',
                               'projectCount': 5,
                               'projectKarmaTotal': 0}
    
# ---- /creator/{creatorName}/projects Endpoint Tests ----
def test_creator_nonexistent_username_projects():
    creator_name = "nonexistent"
    response = client.get(f"/creator/{creator_name}/projects")
    assert response.status_code == 404
    assert response.json() == {"detail":"Creator doesn't exist."}


@patch("app.views_user_api.sqlconn")
def test_creator_existing_username_projects(mock_sqlconn):
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {"creator_id": 123, "profile_picture": "mock_pic.jpg", "join_date": datetime(2024, 10, 16, 14, 43, 8)}
    ]
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchall.side_effect = [
        [{'id': '639638dfa0b464bdc8fd81eb3e951d5f', 'creator': 'incurious', 'creator_id': 26, 'title': 'Wonderful',
        'created_at': datetime(2024, 10, 19, 18, 24, 30), 'likes': 1},
         {'id': 'a15d9c0583d560433464fbe84449a327', 'creator': 'incurious', 'creator_id': 26, 'title': 'Amazing Image',
           'created_at': datetime(2024, 10, 19, 18, 25, 22), 'likes': 1}]]
    creator_name = "incurious"
    response = client.get(f"/creator/{creator_name}/projects")
    assert response.status_code == 200
    assert response.json() == {"projects":[{"id":"639638dfa0b464bdc8fd81eb3e951d5f","creator":"incurious","creator_id":26,"title":"Wonderful",
                                            "created_at":"2024-10-19T18:24:30","likes":1},
                                           {"id":"a15d9c0583d560433464fbe84449a327","creator":"incurious","creator_id":26,"title":"Amazing Image",
                                            "created_at":"2024-10-19T18:25:22","likes":1}]}

# ---- /project/{projectId}/like Endpoint Tests ----

def test_like_project_wrong_jwt():
    jwt = "wrong_jwt"
    project_id = "1"
    response = client.post(f"/project/project/{project_id}/like",headers={"Authorization":jwt})
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_like_project_correct_jwt_no_likes(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        None
    ]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.post(f"/project/project/{project_id}/like",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Liked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_like_project_correct_jwt_liked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Like'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.post(f"/project/project/{project_id}/like",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Unliked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_like_project_correct_jwt_disliked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Dislike'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.post(f"/project/project/{project_id}/like",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Liked"}

# ---- /project/{projectId}/dislike Endpoint Tests ----

def test_dislike_project_wrong_jwt():
    jwt = "wrong_jwt"
    project_id = "1"
    response = client.post(f"/project/project/{project_id}/dislike",headers={"Authorization":jwt})
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_dislike_project_correct_jwt_no_likes(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        None
    ]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.post(f"/project/project/{project_id}/dislike",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Disliked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_dislike_project_correct_jwt_liked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Like'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.post(f"/project/project/{project_id}/dislike",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Disliked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_dislike_project_correct_jwt_disliked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Dislike'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.post(f"/project/project/{project_id}/dislike",headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Undisliked"}


# ---- /project/{project_id}/comments Endpoint Tests ----

def test_get_project_comments_no_jwt_nonexisting_project_id():
    project_id = "1"
    #since project id's are md5 hashes, there cant be a project id with 1,
    #so it will consistently return an empty array even with the real sql connection
    response = client.get(f"/project/project/{project_id}/comments")
    assert response.status_code == 200
    assert response.json() == {"replies":[]}

@patch("app.views_user_api.sqlconn")
def test_get_project_comments_no_jwt_existing_project_id(mock_sqlconn):
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchall.side_effect = [
        [{'id': 22, 'parent_id': 0, 'username': 'incurious', 'content': 'This is nice.', 'likes': 1, 'replies': 3, 'changed_at': datetime(2024, 10, 20, 18, 54, 51), 'l_d': None},
        {'id': 30, 'parent_id': 0, 'username': 'incurious', 'content': 'This is not nice.', 'likes': 1, 'replies': 0, 'changed_at': datetime(2024, 10, 20, 22, 47, 21), 'l_d': None}]]
    project_id = "valid_project_id"
    response = client.get(f"/project/project/{project_id}/comments")
    assert response.status_code == 200
    assert response.json() == {"replies": [
        {
            "id": 22,
            "parent_id": 0,
            "username": "incurious",
            "content": "This is nice.",
            "likes": 1,
            "replies": 3,
            "changed_at": "2024-10-20T18:54:51",
            "l_d": None
        },
        {
            "id": 30,
            "parent_id": 0,
            "username": "incurious",
            "content": "This is not nice.",
            "likes": 1,
            "replies": 0,
            "changed_at": "2024-10-20T22:47:21",
            "l_d": None
        }]}
@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_get_project_comments_correct_jwt_existing_project_id(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchall.side_effect = [
        [{'id': 22, 'parent_id': 0, 'username': 'incurious', 'content': 'This is nice.', 'likes': 1, 'replies': 3, 'changed_at': datetime(2024, 10, 20, 18, 54, 51), 'l_d': "Like"},
        {'id': 30, 'parent_id': 0, 'username': 'incurious', 'content': 'This is not nice.', 'likes': 1, 'replies': 0, 'changed_at': datetime(2024, 10, 20, 22, 47, 21), 'l_d': "Dislike"}]]
    project_id = "valid_project_id"
    response = client.get(f"/project/project/{project_id}/comments")
    assert response.status_code == 200
    assert response.json() == {"replies": [
        {
            "id": 22,
            "parent_id": 0,
            "username": "incurious",
            "content": "This is nice.",
            "likes": 1,
            "replies": 3,
            "changed_at": "2024-10-20T18:54:51",
            "l_d": "Like"
        },
        {
            "id": 30,
            "parent_id": 0,
            "username": "incurious",
            "content": "This is not nice.",
            "likes": 1,
            "replies": 0,
            "changed_at": "2024-10-20T22:47:21",
            "l_d": "Dislike"
        }]}
    

# ---- /project/comment POST Endpoint Tests ----

def test_create_project_comment_no_jwt_no_data():
    response = client.post(f"/project/project/comment")
    assert response.status_code == 422

def test_create_project_comment_no_jwt_correct_data():
    request_json = {"parent_id": 0, "project_id": "1", "content": "Test Comment"}
    response = client.post(f"/project/project/comment",json = request_json)
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

@patch("app.views_user_api.ProjectComment")
@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_create_project_comment_correct_jwt_correct_data(mock_sqlconn,mock_check_auth,mock_ProjectComment):
    request_json = {"parent_id": 0, "project_id": "1", "content": "Test Comment"}
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    response = client.post(f"/project/project/comment",json = request_json)
    assert response.status_code == 200
    assert response.json() == {'id': 1, 'msg': 'Comment created successfully'}

@patch("app.views_user_api.ProjectComment")
@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_create_project_comment_correct_jwt_correct_data_long(mock_sqlconn,mock_check_auth,mock_ProjectComment):
    request_json = {"parent_id": 0, "project_id": "1", "content": "Test Comment\n\n\n\n\n\nHello"}
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    response = client.post(f"/project/project/comment",json = request_json)
    assert response.status_code == 200
    assert response.json() == {'id': 1, 'msg': 'Comment created successfully'}

# ---- /project/comment DELETE Endpoint Tests ----

def test_delete_project_comment_nonexistent_data():
    response = client.delete(f"/project/project/comment")
    assert response.status_code == 422

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_delete_project_comment_correct_jwt_correct_nonexistent_data(mock_sqlconn,mock_check_auth):
    comment_id = 0
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        None
    ]
    response = client.delete(f"/project/project/comment", params={"comment_id":comment_id})
    assert response.status_code == 404
    assert response.json() == {'detail': "You can't delete what doesn't exist."}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_delete_project_comment_correct_jwt_wrong_user_correct_data(mock_sqlconn,mock_check_auth):
    comment_id = 0
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {"user_id":-2}
    ]
    response = client.delete(f"/project/project/comment", params={"comment_id":comment_id})
    assert response.status_code == 403
    assert response.json() == {'detail': "You can't delete a comment someone else created."}


@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_delete_project_comment_correct_jwt_correct_user_correct_data(mock_sqlconn,mock_check_auth):
    comment_id = 0
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {"user_id":-1,"parent_id":-1}
    ]
    response = client.delete(f"/project/project/comment", params={"comment_id":comment_id})
    assert response.status_code == 200
    assert response.json() == {'msg': "Deleted comment"}

# ---- /project/comment/{comment_id} PUT Endpoint Tests ----

def test_put_project_comment_wrong_data():
    response = client.put(f"/project/project/comment/test")
    assert response.status_code == 422

def test_put_project_comment_wrong_json_data():
    response = client.put(f"/project/project/comment/1",json={"content":1})
    assert response.status_code == 422

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_put_project_comment_correct_jwt_correct_nonexistent_data(mock_sqlconn,mock_check_auth):
    comment_id = 0
    request_json = {"content":"test"}
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        None
    ]
    response = client.put(f"/project/project/comment/{comment_id}",json=request_json)
    assert response.status_code == 404
    assert response.json() == {'detail': "You can't edit what doesn't exist."}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_put_project_comment_correct_jwt_wrong_user_correct_data(mock_sqlconn,mock_check_auth):
    comment_id = 0
    request_json = {"content":"test"}
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {"user_id":-2}
    ]
    response = client.put(f"/project/project/comment/{comment_id}",json=request_json)
    assert response.status_code == 403
    assert response.json() == {'detail': "You can't edit a comment someone else created."}


@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_put_project_comment_correct_jwt_correct_user_correct_data(mock_sqlconn,mock_check_auth):
    comment_id = 0
    request_json = {"content":"test"}
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        {"user_id":-1,"parent_id":-1}
    ]
    response = client.put(f"/project/project/comment/{comment_id}",json=request_json)
    assert response.status_code == 200
    assert response.json() == {'msg': "Updated comment"}


# ---- /project/{projectId}/comment/like Endpoint Tests ----
def test_like_project_comment_no_param():
    project_id = "1"
    response = client.get(f"/project/project/{project_id}/comment/like")
    assert response.status_code == 422

def test_like_project_comment_wrong_jwt():
    jwt = "wrong_jwt"
    project_id = "1"
    response = client.get(f"/project/project/{project_id}/comment/like",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_like_project_comment_correct_jwt_no_likes(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        None
    ]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.get(f"/project/project/{project_id}/comment/like",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Liked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_like_project_comment_correct_jwt_liked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Like'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.get(f"/project/project/{project_id}/comment/like",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Unliked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_like_project_comment_correct_jwt_disliked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Dislike'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.get(f"/project/project/{project_id}/comment/like",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Liked2"}


# ---- /project/{projectId}/comment/dislike Endpoint Tests ----
def test_dislike_project_comment_no_param():
    project_id = "1"
    response = client.get(f"/project/project/{project_id}/comment/dislike")
    assert response.status_code == 422

def test_dislike_project_comment_wrong_jwt():
    jwt = "wrong_jwt"
    project_id = "1"
    response = client.get(f"/project/project/{project_id}/comment/dislike",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 401
    assert response.json() == {"detail":"Can't get the user because token is expired or wrong."}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_dislike_project_comment_correct_jwt_no_likes(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [
        None
    ]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.get(f"/project/project/{project_id}/comment/dislike",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Disliked"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_dislike_project_comment_correct_jwt_liked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Like'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.get(f"/project/project/{project_id}/comment/dislike",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Disliked2"}

@patch("app.views_user_api.check_auth")
@patch("app.views_user_api.sqlconn")
def test_dislike_project_comment_correct_jwt_disliked_already(mock_sqlconn,mock_check_auth):
    mock_check_auth.return_value = {"user": -1}
    mock_sql_instance = MagicMock()
    mock_sqlconn.return_value.__enter__.return_value = mock_sql_instance
    mock_sql_instance.session.execute.return_value.mappings.return_value.fetchone.side_effect = [{'l_d': 'Dislike'}]
    jwt = "correct_jwt"
    project_id = "1e2"
    
    response = client.get(f"/project/project/{project_id}/comment/dislike",params={"comment_id":0},headers={"Authorization":jwt})
    assert response.status_code == 200
    assert response.json() == {"msg":"Undisliked"}