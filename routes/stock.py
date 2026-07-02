from flask import render_template, request, redirect
from MySQLdb.cursors import DictCursor
from datetime import datetime

def register_stock_routes(app, mysql):

    @app.route("/receive_stock", methods=["GET", "POST"]
    )
    def receive_stock():
        cur = mysql.connection.cursor(DictCursor)
        if request.method == "POST":
            product_id = request.form["product_id"]
            quantity_received = int(request.form["quantity_received"])
            buying_price = float(request.form["buying_price"])

            cur.execute(
                "SELECT * FROM products WHERE id=%s",
                (product_id,)
            )
            product = cur.fetchone()
            supplier = product["supplier"]

            new_stock = product["stock"] + quantity_received
            cur.execute(
                """UPDATE products SET stock=%s, buying_price=%s WHERE id=%s""",
                (new_stock, buying_price, product_id)
            )

            now = datetime.now()
            receipt_date = now.strftime("%Y-%m-%d")
            receipt_time = now.strftime("%H:%M:%S")

            cur.execute(
                """INSERT INTO stock_receipts
                (product_id, quantity_received, buying_price, supplier, receipt_date, receipt_time) VALUES (%s, %s, %s, %s, %s, %s)""",
                (product_id, quantity_received, buying_price, supplier, receipt_date, receipt_time)
            )
            mysql.connection.commit()
            cur.close()
            return redirect("/products")
        
        cur.execute("""SELECT * FROM products where status='Active'""")
        products = cur.fetchall()
        cur.close()
        return render_template("receive_stock.html", products=products)
    

