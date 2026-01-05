from datetime import datetime

CURRENT_AUTHORIZER = {
    "name": "Rahul Verma",
    "role": "DATC Flight Authorization Officer"
}

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
