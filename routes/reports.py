from flask import render_template, request
from MySQLdb.cursors import DictCursor
from datetime import datetime


def register_report_routes(app, mysql):

    # ==========================================
    # SALES HISTORY
    # ==========================================
    @app.route("/sales_history")
    def sales_history():

        cur = mysql.connection.cursor(DictCursor)

        cur.execute("""
            SELECT
                s.id,
                s.sales_date,
                s.sales_time,
                s.payment_method,
                s.bartender,
                p.product_name,
                si.quantity,
                si.unit_price,
                (si.quantity * si.unit_price) AS total
            FROM sales s
            JOIN sales_items si
                ON s.id = si.sale_id
            JOIN products p
                ON p.id = si.product_id
            ORDER BY s.id DESC
        """)

        sales = cur.fetchall()

        cur.close()

        return render_template(
            "sales_history.html",
            sales=sales
        )

    # ==========================================
    # DAILY SALES REPORT
    # ==========================================
    @app.route("/daily_sales_report")
    def daily_sales_report():

        selected_date = request.args.get(
            "date",
            datetime.now().strftime("%Y-%m-%d")
        )

        cur = mysql.connection.cursor(DictCursor)

        cur.execute("""
            SELECT
                p.product_name,
                SUM(si.quantity) AS quantity_sold,
                si.unit_price,
                SUM(si.quantity * si.unit_price) AS total_sales
            FROM sales s
            JOIN sales_items si
                ON s.id = si.sale_id
            JOIN products p
                ON p.id = si.product_id
            WHERE s.sales_date=%s
            GROUP BY p.product_name, si.unit_price
            ORDER BY total_sales DESC
        """, (selected_date,))

        report = cur.fetchall()

        cur.execute("""
            SELECT COUNT(*) AS total_transactions
            FROM sales
            WHERE sales_date=%s
        """, (selected_date,))

        total_transactions = cur.fetchone()["total_transactions"]

        cur.execute("""
            SELECT SUM(total_amount) AS grand_total
            FROM sales
            WHERE sales_date=%s
        """, (selected_date,))

        grand_total = cur.fetchone()["grand_total"]

        if grand_total is None:
            grand_total = 0

        cur.close()

        return render_template(
            "daily_sales_report.html",
            report=report,
            selected_date=selected_date,
            grand_total=grand_total,
            total_transactions=total_transactions
        )
        # ==========================================
    # DATE RANGE SALES REPORT
    # ==========================================
    @app.route("/date_range_report")
    def date_range_report():

        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")

        cur = mysql.connection.cursor(DictCursor)

        report = []
        total_transactions = 0
        grand_total = 0

        if start_date and end_date:

            cur.execute("""
                SELECT
                    p.product_name,
                    SUM(si.quantity) AS quantity_sold,
                    si.unit_price,
                    SUM(si.quantity * si.unit_price) AS total_sales
                FROM sales s
                JOIN sales_items si
                    ON s.id = si.sale_id
                JOIN products p
                    ON p.id = si.product_id
                WHERE s.sales_date BETWEEN %s AND %s
                GROUP BY p.product_name, si.unit_price
                ORDER BY total_sales DESC
            """, (start_date, end_date))

            report = cur.fetchall()

            cur.execute("""
                SELECT COUNT(*) AS total_transactions
                FROM sales
                WHERE sales_date BETWEEN %s AND %s
            """, (start_date, end_date))

            total_transactions = cur.fetchone()["total_transactions"]

            cur.execute("""
                SELECT SUM(total_amount) AS grand_total
                FROM sales
                WHERE sales_date BETWEEN %s AND %s
            """, (start_date, end_date))

            grand_total = cur.fetchone()["grand_total"]

            if grand_total is None:
                grand_total = 0

        cur.close()

        return render_template(
            "date_range_report.html",
            report=report,
            start_date=start_date,
            end_date=end_date,
            total_transactions=total_transactions,
            grand_total=grand_total
        )