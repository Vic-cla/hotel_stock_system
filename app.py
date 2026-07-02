from flask import Flask, render_template, request, redirect, session
from flask_mysqldb import MySQL
from routes.products import register_product_routes
from routes.auth import register_auth_routes
from routes.sales import register_sales_routes
from datetime import datetime
from routes.reports import register_report_routes
from routes.stock import register_stock_routes
app = Flask(__name__)
app.secret_key = "victor_hotel_secret_2026"

# ===========================
# DATABASE CONFIGURATION
# ===========================
import os

app.config["MYSQL_HOST"] = os.getenv("MYSQL_HOST", "localhost")
app.config["MYSQL_PORT"] = int(os.getenv("MYSQL_PORT", 3306))
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER", "root")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD", "")
app.config["MYSQL_DB"] = os.getenv("MYSQL_DB", "hotel_stock_system")


mysql = MySQL(app)

register_product_routes(app, mysql)
register_auth_routes(app, mysql)
register_sales_routes(app, mysql)
register_report_routes(app, mysql)
register_stock_routes(app, mysql)


@app.route("/")
def dashboard():

    cur = mysql.connection.cursor()

    # ==========================
    # Total Products
    # ==========================
    cur.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE status='Active'
    """)
    total_products = cur.fetchone()[0]

    # ==========================
    # Total Stock
    # ==========================
    cur.execute("""
        SELECT SUM(stock)
        FROM products
        WHERE status='Active'
    """)
    total_stock = cur.fetchone()[0]

    if total_stock is None:
        total_stock = 0

    # ==========================
    # Low Stock
    # ==========================
    cur.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE stock <= reorder_level
        AND status='Active'
    """)
    low_stock = cur.fetchone()[0]

    # ==========================
    # Today's Date
    # ==========================
    today = datetime.now().strftime("%Y-%m-%d")

    # ==========================
    # Today's Sales
    # ==========================
    cur.execute("""
        SELECT SUM(total_amount)
        FROM sales
        WHERE sales_date=%s
    """, (today,))

    today_sales = cur.fetchone()[0]

    if today_sales is None:
        today_sales = 0

    # ==========================
    # Today's Transactions
    # ==========================
    cur.execute("""
        SELECT COUNT(*)
        FROM sales
        WHERE sales_date=%s
    """, (today,))

    total_transactions = cur.fetchone()[0]

    # ==========================
    # Monthly Sales
    # ==========================
    current_month = datetime.now().strftime("%Y-%m")

    cur.execute("""
        SELECT SUM(total_amount)
        FROM sales
        WHERE sales_date LIKE %s
    """, (current_month + "%",))

    monthly_sales = cur.fetchone()[0]

    if monthly_sales is None:
        monthly_sales = 0

    # ==========================
    # Best Selling Product
    # ==========================
    cur.execute("""
        SELECT
            p.product_name,
            SUM(si.quantity) AS qty
        FROM sales_items si
        JOIN products p
            ON si.product_id = p.id
        GROUP BY p.product_name
        ORDER BY qty DESC
        LIMIT 1
    """)

    best = cur.fetchone()

    if best:
        best_product = best[0]
    else:
        best_product = "No Sales"

        # ==========================
    # Best Selling Product
    # ==========================
    cur.execute("""
        SELECT
            p.product_name,
            SUM(si.quantity) AS qty
        FROM sales_items si
        JOIN products p
            ON si.product_id = p.id
        GROUP BY p.product_name
        ORDER BY qty DESC
        LIMIT 1
    """)

    best = cur.fetchone()

    if best:
        best_product = best[0]
    else:
        best_product = "No Sales"

    # ==========================
    # Last 7 Days Sales
    # ==========================
    cur.execute("""
        SELECT
            sales_date,
            SUM(total_amount) AS total_sales
        FROM sales
        GROUP BY sales_date
        ORDER BY sales_date DESC
        LIMIT 7
    """)

    chart = list(cur.fetchall())

    chart.reverse()

    chart_labels = []
    chart_data = []

    for row in chart:
        chart_labels.append(str(row[0]))
        chart_data.append(float(row[1]))

    cur.close()

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_stock=total_stock,
        low_stock=low_stock,
        today_sales=today_sales,
        total_transactions=total_transactions,
        monthly_sales=monthly_sales,
        best_product=best_product,
        chart_labels=chart_labels,
        chart_data=chart_data
    )




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)