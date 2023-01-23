import uuid
import requests
from flask import Flask, g, render_template, session, request, redirect, url_for
from flask_session import Session  # https://pythonhosted.org/Flask-Session
import msal
import app_config
from models import db, Project, Task
import os
from dotenv import load_dotenv
from utils import filter_tasks_by_status, constStatus
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user") is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

load_dotenv()

app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

db.init_app(app)

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return redirect(url_for("projects"))

@app.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=app_config.SCOPE)
    return render_template("login.html", auth_url=session["flow"]["auth_uri"], version=msal.__version__)

@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("projects"))

@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))

def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)

def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result

app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template

@app.get("/projects")
@login_required
def projects():
    user = session.get("user")
    user_id = user.get("oid")
    projects = Project.query.filter_by(owner_id=user_id).all()
    return render_template('projects.html',projects=projects,user=user)

@app.route("/create", methods=['POST',"GET"])
@login_required
def create_project():
    user = session.get("user")
    user_id = user.get("oid")
    if request.method == 'GET':
        return render_template('project_create.html',project={},user=user,title="Add a new project")
    if request.method == 'POST':
        
        name = request.form.get('name')
        description = request.form.get('description')
        if not name or not description:
            return render_template('problem.html')
        project = Project(name = name, description = description,owner_id =user_id)
        db.session.add(project)
        db.session.commit()
        return redirect(url_for("projects"))
    return render_template('problem.html')

@app.route('/delete/<int:id>')
@login_required
def delete_project(id):
    if not id or id != 0:
        project = Project.query.get(id)
        if not project:
            return render_template('problem.html')
        if project:
            db.session.delete(project)
            db.session.commit()
        return redirect('/')

    return render_template('problem.html')

@app.route('/update/<int:id>', methods=['POST','GET'])
@login_required
def update_project(id):
    user = session.get("user")
    if not id or id != 0:
        project = Project.query.get(id)
        if not project:
            return render_template('problem.html')
        
        if request.method == 'GET':
            return render_template('project_create.html',project=project,user=user,title="Update project")
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            project.name = name
            project.description = description
            db.session.commit()
        return redirect('/')

    return render_template('problem.html')

@app.route('/project/<int:id>', methods=['GET','POST'])
@login_required
def open_project(id):
    user = session.get("user")
    if not id or id != 0:
        if request.method == 'GET':
            project = Project.query.get(id)
            if not project:
                return render_template('problem.html')

            tasks = Task.query.filter_by(project_id=id).order_by(Task.created_at.desc())
            todo_tasks = filter_tasks_by_status(tasks,constStatus.TO_DO)
            inprogress_tasks = filter_tasks_by_status(tasks,constStatus.IN_PROGRESS)
            done_tasks = filter_tasks_by_status(tasks,constStatus.DONE)
            
            return render_template('project_tasks.html',
                todo_tasks=todo_tasks,
                inprogress_tasks=inprogress_tasks,
                done_tasks=done_tasks,
                tasks=tasks, 
                task={},
                project=project,
                user=user
                )
                
        if request.method == 'POST':
            name = request.form.get('name')
            description = request.form.get('description')
            
            task = Task(name = name, description = description,status="TO_DO",project_id=id)
            db.session.add(task)
            db.session.commit()
            return redirect(f'/project/{id}')
    return render_template('problem.html')

@app.route('/task/update/<int:id>/<string:status>')
@login_required
def update_task_status(id,status):
    if not id or id != 0:
        task = Task.query.get(id)
        if task:
            if status =='todo':
                task.status = constStatus.TO_DO
            elif status =='inprogress':
                task.status = constStatus.IN_PROGRESS
            elif status =='done':
                task.status = constStatus.DONE
            else:
                return render_template('problem.html')

            db.session.commit()
            return redirect(f'/project/{task.project_id}')

    return render_template('problem.html')

@app.route('/task/delete/<int:id>')
@login_required
def delete_task(id):
    if not id or id != 0:
        task = Task.query.get(id)
        if not task:
            return render_template('problem.html')

        db.session.delete(task)
        db.session.commit()
        return redirect(f'/project/{task.project_id}')

    return render_template('problem.html')

@app.route('/task/details/<int:id>', methods=['POST','GET'])
@login_required
def details_task(id):
    user = session.get("user")
    if not id or id != 0:

        task = Task.query.get(id)
        if not task:
            return render_template('problem.html')
        project = Project.query.get(task.project_id)
        if task:
            if request.method == 'GET':
                return render_template('task_details.html',task=task, project=project,user=user)
            if request.method == 'POST':
                name = request.form.get('name')
                description = request.form.get('description')
                status = request.form.get('status')
                task.name = name
                task.description = description
                task.status = status
                db.session.commit()
            return redirect(f'/project/{project.id}')
    return render_template('problem.html')


if __name__ == "__main__":
    app.run(port=8000)

