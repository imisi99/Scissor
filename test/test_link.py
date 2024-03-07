from .utils import *
from app.routers.link import get_db,get_user
from starlette import status

app.dependency_overrides[get_db] = overide_get_db
app.dependency_overrides[get_user] = overide_get_user

def test_shorten_url(test_link):

    response = client.post('link/shorten-link',params= {'url_link' : 'https://imisi.com/iubrylbvewiybwvvw'})
    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.json()) == 33

def test_shorten_link_broken_link(test_link):

    response = client.post('link/shorten-link', params= {'url_link' : 'https://dave/vdubsvriubvevr'})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'detail' : 'The Url that you provided is invalid'}

def test_get_original_link(test_link):

    response = client.get('link/shorten-link/get-original', params= {'shortened_url_link' : 'https://scissors.com/qwertyuiopas'})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == 'https://imisioluwa.com/aerwlsdougvs;vnsyvrhghuzbvwga'

def test_get_original_link_broken_link(test_link):

    response = client.get('link/shorten-link/get-original', params= {'shortened_url_link' : 'https://scissors.com/qwertyuiopar'})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail' : 'The link that you provided has no original link linked to it'}

def test_get_all_links(test_link):

    response = client.get('/link/get-all-links')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [{
        'link' : 'https://imisioluwa.com/aerwlsdougvs;vnsyvrhghuzbvwga',
        'short_link' : 'https://scissors.com/qwertyuiopas',
        'custom_link' : 'https://coding.com/qwertyuiopas'
    }]

def test_customize_link(test_link):

    response = client.put('link/shorten-link/customize')

def test_qrcode_generation(test_link):

    response = client.put('link/qrcode-generate', params= {'shortened_url' : 'https://scissors.com/qwertyuiopas'})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == 'The Qrcode for this link has been generated successfully.'


def test_qrcode_generation_broken(test_link):
    
    response = client.put('link/qrcode-generate', params= {'shortened_url' : 'https://scissors.com/qwertyuiopad'})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail' : 'Invalid link!'}


def test_qrcode_viewing(test_link):
    
    response = client.get('link/qrcode', params= {'shortened_url' : 'https://scissors.com/qwertyuiopas'})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail' : 'There is no QR code for the shortened link!'}


def test_qrcode_viewing_broken(test_link):
    
    response = client.get('link/qrcode', params= {'shortened_url' : 'https://scissors.com/qwertyuiopad'})
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {'detail' : 'Invalid link!'}


def test_view_analysis(test_link):

    response = client.get('link/analysis/u', params= {'shortened_url' : 'https://scissors.com/qwertyuiopas'})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'link' : 'https://imisioluwa.com/aerwlsdougvs;vnsyvrhghuzbvwga',
        'short_link': 'https://scissors.com/qwertyuiopas',
        'custom_link': 'https://coding.com/qwertyuiopas',
        'clicks': 0,
        'last_clicked': None,
        'click_location' : []
    }

def test_delete_url(test_link):

    response = client.delete('link/delete/', params= {'shortened_url' : 'https://scissors.com/qwertyuiopas'})
    assert response.status_code == status.HTTP_204_NO_CONTENT


                             
