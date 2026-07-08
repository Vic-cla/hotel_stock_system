from flask import render_template, request, session
from datetime import datetime
from MySQLdb.cursors import DictCursor


def register_sales_routes(app, mysql):

    @app.route("/record_sale", methods=["GET", "POST"])
    def record_sale():

        cur = mysql.connection.cursor(DictCursor)

        if request.method == "POST":

            product_id = request.form["product_id"]
            quantity = int(request.form["quantity"])
            payment_method = request.form["payment_method"]

            # Get selected product
            cur.execute(
                "SELECT * FROM products WHERE id=%s",
                (product_id,)
            )

            product = cur.fetchone()

            # Check if product exists
            if not product:
                cur.close()
                return "<h2>❌ Product not found.</h2>"

            selling_price = product["selling_price"]

            # Check stock
            if quantity > product["stock"]:
                cur.close()

                return f"""
                <h2>❌ Not Enough Stock</h2>

                <p>Available stock: {product['stock']}</p>

                <a href="/record_sale">Go Back</a>
                """

            total = selling_price * quantity

            # Current date and time
            now = datetime.now()
            sale_date = now.strftime("%Y-%m-%d")
            sale_time = now.strftime("%H:%M:%S")

            # Temporary bartender name
            # Logged-in bartender
            bartender = session["fullname"]

            # Insert into sales table
            cur.execute(
                """
                INSERT INTO sales
                (payment_method, total_amount, bartender, sales_date, sales_time)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    payment_method,
                    total,
                    bartender,
                    sale_date,
                    sale_time
                )
            )

            sale_id = cur.lastrowid

            # Insert into sale_items table
            cur.execute(
                """
                INSERT INTO sales_items
                (sale_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    sale_id,
                    product_id,
                    quantity,
                    selling_price
                )
            )

            # Update stock
            new_stock = product["stock"] - quantity

            cur.execute(
                """
                UPDATE products
                SET stock=%s
                WHERE id=%s
                """,
                (
                    new_stock,
                    product_id
                )
            )

            mysql.connection.commit()

            cur.close()

            return f"""
            <h2>✅ Sale Completed!</h2>

            <p><strong>Product:</strong> {product['product_name']}</p>

            <p><strong>Quantity:</strong> {quantity}</p>

            <p><strong>Total:</strong> KSh {total}</p>

            <p><strong>Payment:</strong> {payment_method}</p>

            <br>

            <a href="/record_sale">Record Another Sale</a>
            """

        # Load all active products
        cur.execute("""
            SELECT *
            FROM products
            WHERE status='Active'
        """)

        products = cur.fetchall()

        cur.close()

        return render_template(
            "record_sale.html",
            products=products
        )