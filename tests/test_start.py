from app import app

def test_home_login():
    response = app.test_client().get('/',follow_redirects=True)
    print(response.data)
    assert b'Sign In' in response.data

    assert response.status_code==200

def test_create_project():
    with app.test_client() as c:
        with c.session_transaction() as session:
            session["user"] ={"name":"admin-test","oid":"admin-test123"}
        response = c.get('/projects')

        assert b'admin-test' in response.data
        assert b'Your projects' in response.data
        assert response.status_code==200