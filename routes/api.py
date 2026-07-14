import json
import threading
from datetime import datetime
from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import login_required, current_user
from models import db
from models.task import ScrapingTask
from models.business import Business
from models.wa_template import WaTemplate
from models.wa_link import WaLink
from models.wa_click import WaClick
from config.settings import REDIS_HOST, REDIS_PORT, REDIS_DB

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/analytics/<int:upload_id>/chart")
@login_required
def analytics_chart(upload_id):
    from models.data_upload import DataUpload
    from models.data_record import DataRecord
    from collections import Counter, defaultdict
    import statistics

    upload = DataUpload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()
    records = DataRecord.query.filter_by(upload_id=upload_id).all()
    data = [r.data for r in records]
    data_type = upload.data_type

    def safe_float(v, default=0):
        try:
            return float(v) if v is not None else default
        except (ValueError, TypeError):
            return default

    def calc_percentile(values, p):
        if not values:
            return 0
        sorted_v = sorted(values)
        k = (len(sorted_v) - 1) * (p / 100)
        f = int(k)
        c = f + 1
        if c >= len(sorted_v):
            return sorted_v[f]
        return sorted_v[f] + (k - f) * (sorted_v[c] - sorted_v[f])

    def generate_insights(metrics):
        insights = []
        if data_type == "product":
            if metrics.get("low_stock", 0) > 0:
                insights.append({"icon": "⚠️", "type": "warning", "text": f"{metrics['low_stock']} produk stok rendah (<10). Segera lakukan restock."})
            if metrics.get("avg_price", 0) > 0:
                insights.append({"icon": "💰", "type": "info", "text": f"Harga rata-rata Rp {metrics['avg_price']:,.0f}. Pertimbangkan strategi pricing berdasarkan kategori."})
            cats = metrics.get("categories", {}).get("labels", [])
            if len(cats) > 1:
                insights.append({"icon": "📊", "type": "success", "text": f"Produk terdiversi dalam {len(cats)} kategori. Analisis performa per kategori untuk optimasi."})
        elif data_type == "sales":
            rev = metrics.get("total_revenue", 0)
            total = metrics.get("total", 0)
            if total > 0:
                avg = rev / total
                insights.append({"icon": "📈", "type": "success", "text": f"Rata-rata Revenue per Transaksi: Rp {avg:,.0f}. Targetkan peningkatan 10-20%."})
            growth = metrics.get("growth_rate", 0)
            if growth > 0:
                insights.append({"icon": "🚀", "type": "success", "text": f"Pertumbuhan positif {growth:.1f}% menunjukkan tren pasar yang baik."})
            elif growth < 0:
                insights.append({"icon": "📉", "type": "warning", "text": f"Pertumbuhan negatif {growth:.1f}%. Evaluasi strategi marketing dan penjualan."})
            top = metrics.get("top_products", {}).get("labels", [])
            if top:
                insights.append({"icon": "🏆", "type": "info", "text": f"Produk terlaris: {top[0]}. Fokuskan promosi pada produk ini."})
        elif data_type == "customer":
            total = metrics.get("total", 0)
            avg = metrics.get("avg_purchase", 0)
            if total > 0:
                insights.append({"icon": "👥", "type": "info", "text": f"Total {total} pelanggan dengan rata-rata pembelian Rp {avg:,.0f}."})
            segments = metrics.get("segments", {})
            vip = segments.get("vip", 0)
            if vip > 0:
                insights.append({"icon": "⭐", "type": "success", "text": f"{vip} pelanggan VIP (>Rp 2M). Berikan program loyalitas khusus."})
            completeness = metrics.get("completeness", {})
            phone_pct = (completeness.get("phone", 0) / total * 100) if total > 0 else 0
            if phone_pct < 80:
                insights.append({"icon": "📞", "type": "warning", "text": f"Hanya {phone_pct:.0f}% data telepon terisi. Lengkapi data untuk follow-up marketing."})
        elif data_type == "finance":
            balance = metrics.get("balance", 0)
            if balance > 0:
                insights.append({"icon": "✅", "type": "success", "text": f"Keuangan sehat! Surplus Rp {balance:,.0f}."})
            else:
                insights.append({"icon": "⚠️", "type": "warning", "text": f"Defisit Rp {abs(balance):,.0f}. Perlu kontrol pengeluaran."})
            margin = metrics.get("profit_margin", 0)
            if margin > 0:
                insights.append({"icon": "📊", "type": "info", "text": f"Profit margin: {margin:.1f}%. {('Sangat baik' if margin > 30 else 'Cukup' if margin > 10 else 'Perlu ditingkatkan')}."})
        return insights

    if data_type == "product":
        categories = Counter(d.get("category", "Lainnya") for d in data if d.get("category"))
        prices = [safe_float(d.get("price")) for d in data if d.get("price") is not None]
        stocks = [safe_float(d.get("stock"), -1) for d in data if d.get("stock") is not None]
        valid_stocks = [s for s in stocks if s >= 0]

        price_ranges = {"< 25K": 0, "25K-50K": 0, "50K-100K": 0, "100K-250K": 0, "> 250K": 0}
        for p in prices:
            if p < 25000: price_ranges["< 25K"] += 1
            elif p < 50000: price_ranges["25K-50K"] += 1
            elif p < 100000: price_ranges["50K-100K"] += 1
            elif p < 250000: price_ranges["100K-250K"] += 1
            else: price_ranges["> 250K"] += 1

        cat_values = list(categories.values())
        cat_stats = {
            "total_categories": len(categories),
            "avg_per_category": round(statistics.mean(cat_values), 1) if cat_values else 0,
            "max_category": max(cat_values) if cat_values else 0,
            "min_category": min(cat_values) if cat_values else 0,
        }

        stock_health = {"critical": 0, "low": 0, "medium": 0, "high": 0}
        for s in valid_stocks:
            if s < 5: stock_health["critical"] += 1
            elif s < 10: stock_health["low"] += 1
            elif s < 50: stock_health["medium"] += 1
            else: stock_health["high"] += 1

        top_products = sorted([d for d in data if d.get("name")], key=lambda x: safe_float(x.get("price")), reverse=True)[:10]

        metrics = {
            "type": "product",
            "total": len(data),
            "categories": {"labels": list(categories.keys()), "values": list(categories.values())},
            "avg_price": round(statistics.mean(prices), 2) if prices else 0,
            "median_price": round(statistics.median(prices), 2) if prices else 0,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "price_std": round(statistics.stdev(prices), 2) if len(prices) > 1 else 0,
            "price_ranges": {"labels": list(price_ranges.keys()), "values": list(price_ranges.values())},
            "low_stock": sum(1 for s in valid_stocks if s < 10),
            "total_stock": sum(valid_stocks),
            "avg_stock": round(statistics.mean(valid_stocks), 1) if valid_stocks else 0,
            "stock_health": {"labels": ["Kritis (<5)", "Rendah (5-10)", "Sedang (10-50)", "Tinggi (>50)"], "values": [stock_health["critical"], stock_health["low"], stock_health["medium"], stock_health["high"]]},
            "cat_stats": cat_stats,
            "top_products": top_products,
            "insights": [],
        }
        metrics["insights"] = generate_insights(metrics)
        return jsonify(metrics)

    if data_type == "sales":
        monthly = defaultdict(float)
        daily = defaultdict(float)
        weekly = defaultdict(lambda: defaultdict(float))
        product_sales = Counter()
        product_revenue = defaultdict(float)
        customer_sales = defaultdict(float)
        total_revenue = 0
        quantities = []

        for d in data:
            date_str = str(d.get("date", ""))
            total = safe_float(d.get("total_price"))
            qty = int(safe_float(d.get("quantity")))
            pname = d.get("product_name", "Unknown")
            cust = d.get("customer_name", "Unknown")

            total_revenue += total
            quantities.append(qty)
            product_sales[pname] += qty
            product_revenue[pname] += total
            customer_sales[cust] += total

            if date_str and len(date_str) >= 7:
                monthly[date_str[:7]] += total
            if date_str and len(date_str) >= 10:
                daily[date_str] += total
            if date_str and len(date_str) >= 10:
                from datetime import datetime
                try:
                    dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    week_key = f"W{dt.isocalendar()[1]}"
                    weekly[dt.strftime("%Y")][week_key] += total
                except ValueError:
                    pass

        sorted_months = sorted(monthly.items())
        growth_rate = 0
        if len(sorted_months) >= 2:
            prev = sorted_months[-2][1]
            curr = sorted_months[-1][1]
            if prev > 0:
                growth_rate = ((curr - prev) / prev) * 100

        daily_values = list(daily.values())
        sorted_customers = sorted(customer_sales.items(), key=lambda x: x[1], reverse=True)

        revenue_percentiles = {
            "p25": calc_percentile(daily_values, 25),
            "p50": calc_percentile(daily_values, 50),
            "p75": calc_percentile(daily_values, 75),
            "p90": calc_percentile(daily_values, 90),
        }

        top_products_labels = [p[0] for p in product_sales.most_common(10)]
        top_products_qty = [p[1] for p in product_sales.most_common(10)]
        top_products_rev = [product_revenue[p[0]] for p in product_sales.most_common(10)]

        metrics = {
            "type": "sales",
            "total": len(data),
            "total_revenue": total_revenue,
            "avg_transaction": round(total_revenue / len(data), 2) if data else 0,
            "median_transaction": round(statistics.median([safe_float(d.get("total_price")) for d in data]), 2) if data else 0,
            "total_quantity": sum(quantities),
            "avg_quantity": round(statistics.mean(quantities), 1) if quantities else 0,
            "unique_products": len(product_sales),
            "unique_customers": len(customer_sales),
            "growth_rate": round(growth_rate, 2),
            "revenue_percentiles": revenue_percentiles,
            "monthly": {"labels": [m[0] for m in sorted_months], "values": [m[1] for m in sorted_months]},
            "daily": {"labels": sorted(daily.keys())[-30:], "values": [daily[k] for k in sorted(daily.keys())[-30:]]},
            "top_products": {"labels": top_products_labels, "quantity": top_products_qty, "revenue": top_products_rev},
            "top_customers": {"labels": [c[0] for c in sorted_customers[:10]], "values": [c[1] for c in sorted_customers[:10]]},
            "customer_concentration": round((sorted_customers[0][1] / total_revenue * 100) if sorted_customers and total_revenue > 0 else 0, 1),
            "insights": [],
        }
        metrics["insights"] = generate_insights(metrics)
        return jsonify(metrics)

    if data_type == "customer":
        total_purchase_values = [safe_float(d.get("total_purchase")) for d in data]
        total_purchase = sum(total_purchase_values)
        has_phone = sum(1 for d in data if d.get("phone"))
        has_email = sum(1 for d in data if d.get("email"))
        has_address = sum(1 for d in data if d.get("address"))

        segments = {"vip": 0, "regular": 0, "new": 0, "at_risk": 0}
        for v in total_purchase_values:
            if v >= 2000000: segments["vip"] += 1
            elif v >= 500000: segments["regular"] += 1
            elif v >= 100000: segments["new"] += 1
            else: segments["at_risk"] += 1

        purchase_ranges = {"< 100K": 0, "100K-500K": 0, "500K-1M": 0, "1M-2M": 0, "> 2M": 0}
        for v in total_purchase_values:
            if v < 100000: purchase_ranges["< 100K"] += 1
            elif v < 500000: purchase_ranges["100K-500K"] += 1
            elif v < 1000000: purchase_ranges["500K-1M"] += 1
            elif v < 2000000: purchase_ranges["1M-2M"] += 1
            else: purchase_ranges["> 2M"] += 1

        top_customers = sorted([d for d in data if d.get("name")], key=lambda x: safe_float(x.get("total_purchase", 0)), reverse=True)[:10]

        avg_purchase = total_purchase / len(data) if data else 0
        top20_count = max(1, int(len(data) * 0.2))
        top20_sorted = sorted(total_purchase_values, reverse=True)
        top20_revenue = sum(top20_sorted[:top20_count])
        pareto_ratio = round((top20_revenue / total_purchase * 100) if total_purchase > 0 else 0, 1)

        metrics = {
            "type": "customer",
            "total": len(data),
            "total_purchase": total_purchase,
            "avg_purchase": round(avg_purchase, 2),
            "median_purchase": round(statistics.median(total_purchase_values), 2) if total_purchase_values else 0,
            "max_purchase": max(total_purchase_values) if total_purchase_values else 0,
            "min_purchase": min(total_purchase_values) if total_purchase_values else 0,
            "segments": {"labels": ["VIP (>2M)", "Regular (500K-2M)", "New (100K-500K)", "At Risk (<100K)"], "values": [segments["vip"], segments["regular"], segments["new"], segments["at_risk"]]},
            "purchase_ranges": {"labels": list(purchase_ranges.keys()), "values": list(purchase_ranges.values())},
            "top_customers": top_customers,
            "completeness": {"phone": has_phone, "email": has_email, "address": has_address, "total": len(data)},
            "pareto_ratio": pareto_ratio,
            "ltv_stats": {
                "avg": round(avg_purchase, 0),
                "top10_avg": round(statistics.mean(top20_sorted[:10]), 0) if len(top20_sorted) >= 10 else 0,
                "bottom10_avg": round(statistics.mean(top20_sorted[-10:]), 0) if len(top20_sorted) >= 10 else 0,
            },
            "insights": [],
        }
        metrics["insights"] = generate_insights(metrics)
        return jsonify(metrics)

    if data_type == "finance":
        monthly = defaultdict(lambda: {"income": 0, "expense": 0})
        category_expense = defaultdict(float)
        category_income = defaultdict(float)
        daily_flow = defaultdict(lambda: {"income": 0, "expense": 0})
        total_income = 0
        total_expense = 0

        for d in data:
            date_str = str(d.get("date", ""))
            amount = safe_float(d.get("amount"))
            ftype = str(d.get("type", "")).lower()
            cat = d.get("category", "Lainnya")
            is_income = "masuk" in ftype or "income" in ftype or "pemasukan" in ftype

            if is_income:
                total_income += amount
                category_income[cat] += amount
                if date_str and len(date_str) >= 7:
                    monthly[date_str[:7]]["income"] += amount
                if date_str and len(date_str) >= 10:
                    daily_flow[date_str]["income"] += amount
            else:
                total_expense += amount
                category_expense[cat] += amount
                if date_str and len(date_str) >= 7:
                    monthly[date_str[:7]]["expense"] += amount
                if date_str and len(date_str) >= 10:
                    daily_flow[date_str]["expense"] += amount

        sorted_months = sorted(monthly.items())
        sorted_daily = sorted(daily_flow.items())

        cumulative_balance = []
        running = 0
        for date_key, flows in sorted_daily:
            running += flows["income"] - flows["expense"]
            cumulative_balance.append({"date": date_key, "balance": running})

        profit_margin = ((total_income - total_expense) / total_income * 100) if total_income > 0 else 0
        burn_rate = total_expense / max(len(sorted_months), 1)
        runway_months = (total_income - total_expense) / burn_rate if burn_rate > 0 and total_income > total_expense else 0

        expense_categories = []
        for cat, val in sorted(category_expense.items(), key=lambda x: x[1], reverse=True):
            expense_categories.append({"category": cat, "amount": val, "percent": round(val / total_expense * 100, 1) if total_expense > 0 else 0})

        top_expense_cats = expense_categories[:5]

        metrics = {
            "type": "finance",
            "total": len(data),
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
            "profit_margin": round(profit_margin, 2),
            "burn_rate": round(burn_rate, 0),
            "runway_months": round(runway_months, 1),
            "monthly": {
                "labels": [m[0] for m in sorted_months],
                "income": [m[1]["income"] for m in sorted_months],
                "expense": [m[1]["expense"] for m in sorted_months],
                "balance": [m[1]["income"] - m[1]["expense"] for m in sorted_months],
            },
            "cumulative_balance": cumulative_balance,
            "income_categories": {"labels": list(category_income.keys()), "values": list(category_income.values())},
            "expense_categories": {"labels": list(category_expense.keys()), "values": list(category_expense.values())},
            "top_expense_cats": top_expense_cats,
            "insights": [],
        }
        metrics["insights"] = generate_insights(metrics)
        return jsonify(metrics)

    return jsonify({"type": data_type, "total": len(data), "insights": []})


@api_bp.route("/analytics/<int:upload_id>/records")
@login_required
def analytics_records(upload_id):
    from models.data_upload import DataUpload
    from models.data_record import DataRecord
    upload = DataUpload.query.filter_by(id=upload_id, user_id=current_user.id).first_or_404()
    records = DataRecord.query.filter_by(upload_id=upload_id).limit(500).all()
    return jsonify([r.data for r in records])


@api_bp.route("/task/<int:task_id>/status")
@login_required
def task_status(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return jsonify(task.to_dict())


@api_bp.route("/task/<int:task_id>/businesses")
@login_required
def task_businesses(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    page = request.args.get("page", 1, type=int)
    search = request.args.get("q", "").strip()
    quality = request.args.get("quality", "all").strip()
    lead_status = request.args.get("lead_status", "all").strip()
    query = Business.query.filter_by(task_id=task_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Business.name.ilike(like),
                Business.phone.ilike(like),
                Business.address.ilike(like),
                Business.category.ilike(like),
            )
        )
    if lead_status and lead_status != "all":
        if lead_status == "new":
            query = query.filter(db.or_(Business.lead_status == "new", Business.lead_status.is_(None)))
        else:
            query = query.filter(Business.lead_status == lead_status)
    if quality == "with_phone":
        query = query.filter(Business.phone.isnot(None), Business.phone != "")
    elif quality == "contacted":
        query = query.filter(Business.last_contacted_at.isnot(None))
    elif quality == "hot":
        query = query.filter(
            Business.phone.isnot(None),
            Business.phone != "",
            db.or_(Business.rating >= 4.5, Business.review_count >= 20),
        )
    elif quality == "warm":
        query = query.filter(
            Business.phone.isnot(None),
            Business.phone != "",
            db.or_(Business.rating >= 4.0, Business.review_count >= 5),
        )
    query = query.order_by(Business.id.asc())
    paginated = query.paginate(page=page, per_page=25, error_out=False)
    return jsonify({
        "businesses": [b.to_dict() for b in paginated.items],
        "total": paginated.total,
        "page": paginated.page,
        "pages": paginated.pages,
    })


@api_bp.route("/task/<int:task_id>/wa-data")
@login_required
def task_wa_data(task_id):
    task = ScrapingTask.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    templates = WaTemplate.query.filter_by(user_id=current_user.id, is_active=True).all()
    template_list = []
    for t in templates:
        links = WaLink.query.filter_by(template_id=t.id, is_active=True).all()
        template_list.append({
            "id": t.id,
            "name": t.name,
            "message": t.message,
            "links": [{"id": l.id, "name": l.name, "url": l.url} for l in links],
        })
    clicks = WaClick.query.filter_by(user_id=current_user.id, task_id=task_id)\
        .order_by(WaClick.clicked_at.desc()).all()
    click_list = []
    for c in clicks:
        click_list.append({
            "business_id": c.business_id,
            "template_id": c.template_id,
            "template_name": c.template.name if c.template else None,
            "link_id": c.link_id,
            "link_name": c.link.name if c.link else None,
            "phone": c.phone,
            "clicked_at": c.clicked_at.isoformat() if c.clicked_at else None,
        })
    return jsonify({"templates": template_list, "clicks": click_list})


@api_bp.route("/businesses/<int:business_id>/lead", methods=["PATCH"])
@login_required
def update_business_lead(business_id):
    business = Business.query.filter_by(id=business_id, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    allowed_statuses = {"new", "sent", "replied", "interested", "followup", "not_interested", "closed"}

    lead_status = data.get("lead_status")
    if lead_status:
        if lead_status not in allowed_statuses:
            return jsonify({"error": "Invalid lead_status"}), 400
        business.lead_status = lead_status

    if "lead_note" in data:
        business.lead_note = (data.get("lead_note") or "").strip()

    if "lead_score" in data:
        try:
            business.lead_score = int(data.get("lead_score") or 0)
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid lead_score"}), 400

    if data.get("mark_contacted"):
        business.last_contacted_at = datetime.utcnow()
        if not business.lead_status or business.lead_status == "new":
            business.lead_status = "sent"

    db.session.commit()
    return jsonify(business.to_dict())


@api_bp.route("/task/<int:task_id>/stream")
@login_required
def task_stream(task_id):
    import redis as redis_lib
    redis_client = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"task:{task_id}")
            pubsub.subscribe(f"task:{task_id}:logs")

            task = ScrapingTask.query.filter_by(id=task_id).first()
            if task:
                yield f"data: {json.dumps(task.to_dict())}\n\n"

            for _ in range(600):
                task = ScrapingTask.query.filter_by(id=task_id).first()
                if not task:
                    break

                if task.status in ("completed", "failed", "cancelled"):
                    yield f"data: {json.dumps(task.to_dict())}\n\n"
                    break

                message = pubsub.get_message(timeout=0.5)
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield f"data: {json.dumps(data)}\n\n"
                    except (json.JSONDecodeError, TypeError):
                        pass

            pubsub.unsubscribe()
            pubsub.close()

    response = Response(generate(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@api_bp.route("/task/<int:task_id>/progress")
@login_required
def task_progress(task_id):
    import redis as redis_lib
    redis_client = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    app = current_app._get_current_object()

    def generate():
        with app.app_context():
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"task:{task_id}")

            task = ScrapingTask.query.filter_by(id=task_id).first()
            if task:
                yield f"data: {json.dumps(task.to_dict())}\n\n"

            last_yield = 0
            for _ in range(3600):
                task = ScrapingTask.query.filter_by(id=task_id).first()
                if not task:
                    break

                now = int(__import__('time').time())
                if now - last_yield >= 1:
                    yield f"data: {json.dumps(task.to_dict())}\n\n"
                    last_yield = now

                if task.status in ("completed", "failed", "cancelled"):
                    yield f"data: {json.dumps(task.to_dict())}\n\n"
                    break

                message = pubsub.get_message(timeout=0.1)
                if message and message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield f"data: {json.dumps(data)}\n\n"
                    except (json.JSONDecodeError, TypeError):
                        pass

            pubsub.unsubscribe()
            pubsub.close()

    response = Response(generate(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


@api_bp.route("/tasks/active")
@login_required
def active_tasks():
    tasks = ScrapingTask.query.filter(
        ScrapingTask.user_id == current_user.id,
        ScrapingTask.status.in_(["pending", "running"])
    ).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.route("/businesses/delete", methods=["POST"])
@login_required
def delete_businesses():
    data = request.get_json()
    ids = data.get("ids", [])
    if not ids:
        return jsonify({"error": "No IDs provided"}), 400
    deleted = Business.query.filter(
        Business.id.in_(ids),
        Business.user_id == current_user.id,
    ).delete(synchronize_session=False)
    db.session.commit()
    return jsonify({"deleted": deleted})
