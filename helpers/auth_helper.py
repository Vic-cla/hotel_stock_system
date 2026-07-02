from functools import wraps
from flask import session, redirect


def roles_required(*roles):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            if "admin" not in session:
                return redirect("/admin_login")

            if session.get("role") not in roles:
                return "<h2>⛔ Access Denied</h2>"

            return f(*args, **kwargs)

        return decorated_function

    return decorator