from .utils import *
from app.routers.user import get_db, get_user, authentication, authorization, timedelta, jwt, Secret, Algorithm
from starlette import status

app.dependency_overrides[get_db] = overide_get_db
app.dependency_overrides[get_user] = overide_get_user


def test_user_signup(test_user):
    form = {
        'firstname': 'Imisioluwa',
        'lastname': 'Isong',
        'username': 'Imisioluwa234',
        'email': 'isongrichard2345@gmail.com',
        'password': 'Imisioluwa234.'
    }

    response = client.post("user/signup", json=form)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == "User has signed up successfully"


def test_get_user_details(test_user):
    response = client.get('/user/user-details')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'firstname': 'Imisioluwa',
        'lastname': 'Isong',
        'username': 'Imisioluwa23',
        'email': 'isongrichard234@gmail.com'
    }


def test_update_user_details(test_user):
    form = {
        'firstname': 'Imisioluwa',
        'lastname': 'Isong',
        'username': 'Imisioluwa234',
        'email': 'isongrichard234@gmail.com'
    }
    response = client.put('user/user-details/update', json=form)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == "User details have been updated successfully."


def test_user_forgot_password(test_user):
    form = {
        'username': 'Imisioluwa23',
        'email': 'isongrichard234@gmail.com',
        'new_password': 'Imisioluwa234.',
        'confirm_password': 'Imisioluwa234.'
    }

    response = client.put('user/forgot-password/recovery', json=form)
    assert response.status_code == status.HTTP_202_ACCEPTED


def test_user_forgot_password_wrong_username(test_user):
    form = {
        'username': 'Imisioluwa234',
        'email': 'isongrichard234@gmail.com',
        'new_password': 'Imisioluwa234.',
        'confirm_password': 'Imisioluwa234.'
    }

    response = client.put('user/forgot-password/recovery', json=form)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Invalid credentials"}


def test_user_forgot_password_not_matching_password(test_user):
    form = {
        'username': 'Imisioluwa23',
        'email': 'isongrichard234@gmail.com',
        'new_password': 'Imisioluwa24.',
        'confirm_password': 'Imisioluwa234.'
    }

    response = client.put('user/forgot-password/recovery', json=form)
    assert response.status_code == status.HTTP_406_NOT_ACCEPTABLE
    assert response.json() == {"detail": "Passwords does not match!"}


def test_change_user_password(test_user):
    response = client.put('user/change-password/',
                          params={'current_password': 'Imisioluwa234.', 'new_password': 'Imisiolluwa23.'})
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == "User password has been updated successfully."


def test_delete_user_account(test_user):
    response = client.delete('user/user/delete-user')
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_authorization(test_user):
    db = test_begin()

    response = authorization(test_user.username, 'Imisioluwa234.', db)
    assert response.username == 'Imisioluwa23'
    assert response.email == 'isongrichard234@gmail.com'


def test_authentication(test_user):
    username = test_user.username
    user_id = test_user.id
    expired = timedelta(minutes=4)

    token = authentication(username, user_id, expired)
    response = jwt.decode(token, Secret, algorithms=[Algorithm])
    assert response['sub'] == 'Imisioluwa23'


@pytest.mark.asyncio
async def test_get_user(test_user):
    token = authentication(test_user.username, test_user.id, timedelta=timedelta(minutes=4))
    response = await get_user(token=token)
    assert response == {'username': 'Imisioluwa23', 'user_id': 1}
