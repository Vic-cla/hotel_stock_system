
from flask import render_template, request, session, redirect, url_for
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from MySQLdb.cursors import DictCursor
from helpers.auth_helper import roles_required


def register_sales_routes(app, mysql):

    @app.route("/record_sale", methods=["GET", "POST"])
    @roles_required("Manager", "Cashier")
    def record_sale():

        cur = mysql.connection.cursor(DictCursor)

        # Load available products for the POS
        def load_products():
            cur.execute("""
                SELECT id, product_name, selling_price, stock
                FROM products
                WHERE status = 'Active' AND stock > 0
                ORDER BY product_name
            """)
            return cur.fetchall()

        if request.method == "POST":

            try:
                # -----------------------------
                # 1. Read and validate form data
                # -----------------------------

                product_ids = request.form.getlist("product_id[]")
                quantities = request.form.getlist("quantity[]")

                payment_method = request.form.get("payment_method", "").strip()
                order_type = request.form.get("order_type", "").strip()
                table_number = request.form.get("table_number", "").strip() or None
                order_reference = request.form.get("order_reference", "").strip() or None

                if not product_ids or len(product_ids) != len(quantities):
                    raise ValueError("Please add at least one product to the bill.")

                if payment_method not in ("Cash", "M-PESA"):
                    raise ValueError("Please select a valid payment method.")

                if order_type not in ("Dine-in", "Takeaway"):
                    raise ValueError("Please select Dine-in or Takeaway.")

                if order_type == "Dine-in" and not table_number:
                    raise ValueError("Please enter the table number.")

                if order_type == "Takeaway" and not order_reference:
                    raise ValueError("Please enter the takeaway order reference.")

                # Combine repeated products into one quantity
                cart_quantities = {}

                for product_id, quantity in zip(product_ids, quantities):

                    try:
                        product_id = int(product_id)
                        quantity = int(quantity)
                    except (ValueError, TypeError):
                        raise ValueError("Invalid product or quantity.")

                    if product_id <= 0 or quantity <= 0:
                        raise ValueError("Product and quantity must be valid.")

                    cart_quantities[product_id] = (
                        cart_quantities.get(product_id, 0) + quantity
                    )

                # -----------------------------
                # 2. Validate discount
                # -----------------------------

                try:
                    discount_percentage = Decimal(
                        request.form.get("discount_percentage", "0") or "0"
                    )
                except InvalidOperation:
                    raise ValueError("Please enter a valid discount percentage.")

                if not discount_percentage.is_finite() or not (
                    Decimal("0") <= discount_percentage <= Decimal("100")
                ):
                    raise ValueError("Discount must be between 0% and 100%.")

                # A discount requires manager approval
                approved_by = None

                if discount_percentage > 0:

                    manager_username = request.form.get(
                        "manager_username", ""
                    ).strip()

                    manager_password = request.form.get(
                        "manager_password", ""
                    )

                    if not manager_username or not manager_password:
                        raise ValueError(
                            "A manager must enter their username and password "
                            "to approve this discount."
                        )

                    cur.execute("""
                        SELECT id, fullname
                        FROM users
                        WHERE username = %s
                          AND password = %s
                          AND role = 'Manager'
                          AND status = 'Active'
                        LIMIT 1
                    """, (manager_username, manager_password))

                    manager = cur.fetchone()

                    if not manager:
                        raise ValueError(
                            "Manager approval failed. Check the manager's "
                            "credentials and try again."
                        )

                    approved_by = manager["id"]

                # -----------------------------
                # 3. Begin database transaction
                # -----------------------------

                mysql.connection.begin()

                cart_items = []
                subtotal = Decimal("0.00")

                # Lock products while checking stock
                for product_id, quantity in cart_quantities.items():

                    cur.execute("""
                        SELECT id, product_name, selling_price, stock, status
                        FROM products
                        WHERE id = %s
                        FOR UPDATE
                    """, (product_id,))

                    product = cur.fetchone()

                    if not product or product["status"] != "Active":
                        raise ValueError(
                            "One of the selected products is unavailable."
                        )

                    if quantity > product["stock"]:
                        raise ValueError(
                            f"Not enough stock for {product['product_name']}. "
                            f"Available stock: {product['stock']}."
                        )

                    unit_price = Decimal(str(product["selling_price"]))
                    line_total = (
                        unit_price * quantity
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                    subtotal += line_total

                    cart_items.append({
                        "product_id": product["id"],
                        "product_name": product["product_name"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total
                    })

                subtotal = subtotal.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

                discount_amount = (
                    subtotal * discount_percentage / Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                total_amount = subtotal - discount_amount

                # -----------------------------
                # 4. Create the sale record
                # -----------------------------

                now = datetime.now()

                cur.execute("""
                    INSERT INTO sales (
                        payment_method,
                        total_amount,
                        bartender,
                        sales_date,
                        sales_time,
                        subtotal,
                        discount_percentage,
                        discount_amount,
                        order_type,
                        table_number,
                        order_reference,
                        approved_by
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    payment_method,
                    total_amount,
                    session["fullname"],
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    subtotal,
                    discount_percentage,
                    discount_amount,
                    order_type,
                    table_number if order_type == "Dine-in" else None,
                    order_reference if order_type == "Takeaway" else None,
                    approved_by
                ))

                sale_id = cur.lastrowid

                # -----------------------------
                # 5. Save sale items and deduct stock
                # -----------------------------

                for item in cart_items:

                    cur.execute("""
                        INSERT INTO sales_items (
                            sale_id,
                            product_id,
                            quantity,
                            unit_price
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        sale_id,
                        item["product_id"],
                        item["quantity"],
                        item["unit_price"]
                    ))

                    cur.execute("""
                        UPDATE products
                        SET stock = stock - %s
                        WHERE id = %s
                          AND status = 'Active'
                          AND stock >= %s
                    """, (
                        item["quantity"],
                        item["product_id"],
                        item["quantity"]
                    ))

                    if cur.rowcount != 1:
                        raise ValueError(
                            f"Stock could not be updated for "
                            f"{item['product_name']}. Please try again."
                        )

                # -----------------------------
                # 6. Commit the complete sale
                # -----------------------------

                mysql.connection.commit()
                cur.close()

                return redirect(url_for("sale_receipt", sale_id=sale_id))

            except ValueError as error:

                mysql.connection.rollback()

                products = load_products()
                cur.close()

                return render_template(
                    "record_sale.html",
                    products=products,
                    error=str(error)
                )

            except Exception:

                mysql.connection.rollback()
                cur.close()

                return (
                    "<h2>Sale could not be completed.</h2>"
                    "<p>No stock should have been deducted. "
                    "Please return to the POS and try again.</p>"
                    '<a href="/record_sale">Back to Record Sale</a>'
                )

        products = load_products()
        cur.close()

        return render_template(
            "record_sale.html",
            products=products
        )

    # ---------------------------------
    # PRINTABLE SALE RECEIPT
    # ---------------------------------

    @app.route("/receipt/<int:sale_id>")
    @roles_required("Manager", "Cashier")
    def sale_receipt(sale_id):

        cur = mysql.connection.cursor(DictCursor)

        cur.execute("""
            SELECT
                s.*,
                u.fullname AS manager_name
            FROM sales s
            LEFT JOIN users u ON u.id = s.approved_by
            WHERE s.id = %s
        """, (sale_id,))

        sale = cur.fetchone()

        if not sale:
            cur.close()
            return "<h2>Receipt not found.</h2>", 404

        cur.execute("""
            SELECT
                p.product_name,
                si.quantity,
                si.unit_price,
                (si.quantity * si.unit_price) AS line_total
            FROM sales_items si
            JOIN products p ON p.id = si.product_id
            WHERE si.sale_id = %s
        """, (sale_id,))

        items = cur.fetchall()
        cur.close()

        return render_template(
            "receipt.html",
            sale=sale,
            items=items
        )
