from flask import render_template, request, redirect, session
from MySQLdb.cursors import DictCursor


def register_auth_routes(app, mysql):

    @app.route("/admin_login", methods=["GET", "POST"])
    def admin_login():

        if request.method == "POST":

            username = request.form["username"]
            password = request.form["password"]

            cur = mysql.connection.cursor(DictCursor)

            cur.execute("""
                SELECT *
                FROM users
                WHERE username=%s
                AND password=%s
                AND status='Active'
            """, (
                username,
                password
            ))

            user = cur.fetchone()

            cur.close()

            if user:

                session["admin"] = True
                session["user_id"] = user["id"]
                session["fullname"] = user["fullname"]
                session["username"] = user["username"]
                session["role"] = user["role"]

                return redirect("/")

            return "❌ Invalid username or password."

        return render_template("admin_login.html")


    @app.route("/logout")
    def logout():

        session.clear()

        return redirect("/admin_login")