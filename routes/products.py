from flask import render_template, request, redirect, session
from MySQLdb.cursors import DictCursor
from helpers.auth_helper import roles_required


def register_product_routes(app, mysql):

    # ==========================
    # VIEW PRODUCTS
    # ==========================
    @app.route("/products")
    @roles_required("Manager", "Storekeeper", "Cashier")
    def home():

        search = request.args.get("search", "")

        cur = mysql.connection.cursor(DictCursor)

        cur.execute("""
            SELECT *
            FROM products
            WHERE status='Active'
            AND (
                product_name LIKE %s
                OR category LIKE %s
                OR supplier LIKE %s
            )
            ORDER BY id DESC
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        ))

        products = cur.fetchall()

        cur.close()

        return render_template(
            "index.html",
            products=products,
            search=search
        )

    # ==========================
    # ADD PRODUCT
    # ==========================
    @app.route("/add_product", methods=["GET", "POST"])
    @roles_required("Manager", "Storekeeper")
    def add_product():

        if request.method == "POST":

            product_name = request.form["product_name"]
            category = request.form["category"]
            buying_price = request.form["buying_price"]
            selling_price = request.form["selling_price"]
            stock = request.form["stock"]
            supplier = request.form["supplier"]
            reorder_level = request.form["reorder_level"]

            cur = mysql.connection.cursor()

            cur.execute("""
                INSERT INTO products
                (
                    product_name,
                    category,
                    buying_price,
                    selling_price,
                    stock,
                    supplier,
                    reorder_level
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                product_name,
                category,
                buying_price,
                selling_price,
                stock,
                supplier,
                reorder_level
            ))

            mysql.connection.commit()
            cur.close()

            return redirect("/products")

        return render_template("add_product.html")

    # ==========================
    # EDIT PRODUCT
    # ==========================
    @app.route("/edit_product/<int:id>", methods=["GET", "POST"])
    @roles_required("Manager", "Storekeeper")
    def edit_product(id):

        cur = mysql.connection.cursor(DictCursor)

        if request.method == "POST":

            product_name = request.form["product_name"]
            category = request.form["category"]
            buying_price = request.form["buying_price"]
            selling_price = request.form["selling_price"]
            stock = request.form["stock"]
            supplier = request.form["supplier"]
            reorder_level = request.form["reorder_level"]
            status = request.form["status"]

            cur.execute("""
                UPDATE products
                SET
                    product_name=%s,
                    category=%s,
                    buying_price=%s,
                    selling_price=%s,
                    stock=%s,
                    supplier=%s,
                    reorder_level=%s,
                    status=%s
                WHERE id=%s
            """, (
                product_name,
                category,
                buying_price,
                selling_price,
                stock,
                supplier,
                reorder_level,
                status,
                id
            ))

            mysql.connection.commit()
            cur.close()

            return redirect("/products")

        cur.execute(
            "SELECT * FROM products WHERE id=%s",
            (id,)
        )

        product = cur.fetchone()

        cur.close()

        return render_template(
            "edit_product.html",
            product=product
        )

    # ==========================
    # DELETE PRODUCT
    # ==========================
    @app.route("/delete_product/<int:id>")
    @roles_required("Manager")
    def delete_product(id):

        cur = mysql.connection.cursor()

        cur.execute("""
            UPDATE products
            SET status='Inactive'
            WHERE id=%s
        """, (id,))

        mysql.connection.commit()
        cur.close()

        return redirect("/products")