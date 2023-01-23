import os

client_id = os.environ['CLIENT_ID']
client_secret = os.environ['CLIENT_SECRET']

SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

b2c_tenant = "aghtest"
signupsignin_user_flow = "B2C_1_signupsignin1"

authority_template = "https://{tenant}.b2clogin.com/{tenant}.onmicrosoft.com/{user_flow}"

CLIENT_ID = client_id

CLIENT_SECRET = client_secret

AUTHORITY = authority_template.format(
    tenant=b2c_tenant, user_flow=signupsignin_user_flow)

REDIRECT_PATH = "/getAToken"

SCOPE = []

SESSION_TYPE = "filesystem"
