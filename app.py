from flask import Flask, render_template, request, jsonify, send_file, make_response
import sqlite3
import os
import csv
import io
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict
import calendar

app = Flask(__name__)
DB_PATH = 'database/expenses.db'


# ═══════════════════════════════════════════════════════════════
#                    DATABASE SETUP
# ═══════════════════════════════════════════════════════════════

def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with all tables."""
    os.makedirs('database', exist_ok=True)
    conn = get_db()
    c = conn.cursor()

    # Expenses table
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        payment_method TEXT DEFAULT 'Cash',
        notes TEXT DEFAULT '',
        is_recurring INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Budgets table
    c.execute('''CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,
        monthly_limit REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Categories table
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '📦',
        color TEXT DEFAULT '#667eea'
    )''')

    # Seed default categories
    default_categories = [
        ('Food', '🍔', '#f5576c'),
        ('Transport', '🚗', '#4facfe'),
        ('Shopping', '🛍️', '#f093fb'),
        ('Bills', '📄', '#43e97b'),
        ('Entertainment', '🎬', '#fa709a'),
        ('Health', '💊', '#38f9d7'),
        ('Education', '📚', '#667eea'),
        ('Travel', '✈️', '#fee140'),
        ('Groceries', '🛒', '#a8ff78'),
        ('Other', '📦', '#764ba2'),
    ]
    for name, icon, color in default_categories:
        c.execute('INSERT OR IGNORE INTO categories (name, icon, color) VALUES (?, ?, ?)',
                  (name, icon, color))

    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════
#              AI-POWERED AUTO CATEGORIZATION
# ═══════════════════════════════════════════════════════════════

# Keyword mapping for AI-style categorization
CATEGORY_KEYWORDS = {
    'Food': ['pizza', 'burger', 'restaurant', 'cafe', 'coffee', 'lunch', 'dinner',
             'breakfast', 'snack', 'starbucks', 'mcdonald', 'kfc', 'food', 'eat',
             'meal', 'dining', 'swiggy', 'zomato', 'uber eats', 'doordash'],
    'Transport': ['uber', 'lyft', 'taxi', 'bus', 'train', 'metro', 'fuel', 'gas',
                  'petrol', 'diesel', 'parking', 'toll', 'cab', 'ride', 'transport'],
    'Shopping': ['amazon', 'flipkart', 'clothes', 'shoes', 'shirt', 'dress', 'mall',
                 'store', 'shop', 'purchase', 'buy', 'ebay', 'walmart', 'target'],
    'Bills': ['electricity', 'water', 'internet', 'wifi', 'phone', 'mobile', 'bill',
              'rent', 'utility', 'insurance', 'subscription', 'netflix', 'spotify'],
    'Entertainment': ['movie', 'cinema', 'theater', 'game', 'concert', 'netflix',
                      'youtube', 'prime', 'disney', 'party', 'fun', 'entertainment'],
    'Health': ['doctor', 'hospital', 'medicine', 'pharmacy', 'gym', 'fitness',
               'dentist', 'clinic', 'health', 'medical', 'prescription'],
    'Education': ['book', 'course', 'tuition', 'school', 'college', 'university',
                  'udemy', 'coursera', 'education', 'training', 'class'],
    'Travel': ['hotel', 'flight', 'airbnb', 'booking', 'trip', 'vacation',
               'holiday', 'travel', 'tour', 'resort'],
    'Groceries': ['grocery', 'supermarket', 'vegetables', 'fruits', 'milk', 'bread',
                  'walmart', 'kroger', 'whole foods', 'big bazaar'],
}


def ai_categorize(description):
    """AI-style categorization based on keywords in description."""
    description_lower = description.lower()
    scores = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in description_lower:
                score += len(keyword)  # Longer matches = higher confidence
        if score > 0:
            scores[category] = score

    if scores:
        best_match = max(scores, key=scores.get)
        return best_match, round(scores[best_match] / 10, 2)

    return 'Other', 0.0


def ai_suggest_savings(expenses):
    """AI-style insights and savings suggestions."""
    insights = []

    if not expenses:
        return ["Start adding expenses to get AI-powered insights!"]

    # Category analysis
    category_totals = defaultdict(float)
    for exp in expenses:
        category_totals[exp['category']] += exp['amount']

    total = sum(category_totals.values())
    if total == 0:
        return insights

    # Find highest spending category
    top_category = max(category_totals, key=category_totals.get)
    top_amount = category_totals[top_category]
    top_pct = (top_amount / total) * 100

    insights.append(
        f"📊 Your highest spending is on **{top_category}** "
        f"({top_pct:.1f}% of total: ${top_amount:.2f})"
    )

    if top_pct > 40:
        insights.append(
            f"💡 Consider reducing **{top_category}** spending — "
            f"it's over 40% of your budget!"
        )

    # Average daily spend
    dates = [datetime.fromisoformat(exp['date']) for exp in expenses]
    if dates:
        days_span = (max(dates) - min(dates)).days + 1
        avg_daily = total / max(days_span, 1)
        insights.append(f"📅 Average daily spend: **${avg_daily:.2f}**")

        projected_monthly = avg_daily * 30
        insights.append(f"🔮 Projected monthly spend: **${projected_monthly:.2f}**")

    # Frequency analysis
    if len(expenses) > 0:
        avg_transaction = total / len(expenses)
        insights.append(f"💰 Average transaction: **${avg_transaction:.2f}**")

    # Small frequent purchases
    small_purchases = [e for e in expenses if e['amount'] < 10]
    if len(small_purchases) > 5:
        small_total = sum(e['amount'] for e in small_purchases)
        insights.append(
            f"☕ You made **{len(small_purchases)} small purchases** "
            f"(under $10) totaling **${small_total:.2f}**. Cutting these could save money!"
        )

    return insights


# ═══════════════════════════════════════════════════════════════
#                       ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


# ─────────────── EXPENSES CRUD ───────────────

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    """Get all expenses with filtering, searching, sorting."""
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    min_amount = request.args.get('min_amount', '').strip()
    max_amount = request.args.get('max_amount', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc').upper()
    limit = request.args.get('limit', type=int)

    query = "SELECT * FROM expenses WHERE 1=1"
    params = []

    if search:
        query += " AND (description LIKE ? OR notes LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    if category:
        query += " AND category = ?"
        params.append(category)

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    if min_amount:
        query += " AND amount >= ?"
        params.append(float(min_amount))

    if max_amount:
        query += " AND amount <= ?"
        params.append(float(max_amount))

    # Safe sort column
    valid_sorts = {'date', 'amount', 'category', 'description', 'id'}
    if sort_by not in valid_sorts:
        sort_by = 'date'
    if order not in ('ASC', 'DESC'):
        order = 'DESC'

    query += f" ORDER BY {sort_by} {order}"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    conn = get_db()
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    expenses_list = [dict(row) for row in rows]
    total = sum(e['amount'] for e in expenses_list)
    avg = total / len(expenses_list) if expenses_list else 0

    return jsonify({
        'expenses': expenses_list,
        'total': round(total, 2),
        'count': len(expenses_list),
        'average': round(avg, 2)
    })


@app.route('/api/expenses', methods=['POST'])
def add_expense():
    """Add a new expense with AI categorization."""
    data = request.json

    description = data.get('description', '').strip()
    if not description:
        return jsonify({'error': 'Description is required'}), 400

    try:
        amount = float(data.get('amount', 0))
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Valid amount is required'}), 400

    category = data.get('category', '').strip()
    ai_confidence = 0.0

    # AI auto-categorize if not provided
    if not category or category == 'Auto':
        category, ai_confidence = ai_categorize(description)

    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')
    payment_method = data.get('payment_method', 'Cash')
    notes = data.get('notes', '')
    is_recurring = 1 if data.get('is_recurring') else 0

    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO expenses
                 (description, amount, category, date, payment_method, notes, is_recurring)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (description, amount, category, date, payment_method, notes, is_recurring))
    new_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'id': new_id,
        'category': category,
        'ai_confidence': ai_confidence,
        'message': f'Expense added to {category}'
    })


@app.route('/api/expenses/<int:expense_id>', methods=['GET'])
def get_expense(expense_id):
    """Get single expense."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Expense not found'}), 404
    return jsonify(dict(row))


@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    """Update an existing expense."""
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Expense not found'}), 404

    fields = []
    params = []
    allowed = ['description', 'amount', 'category', 'date',
               'payment_method', 'notes', 'is_recurring']

    for field in allowed:
        if field in data:
            fields.append(f"{field} = ?")
            params.append(data[field])

    if not fields:
        conn.close()
        return jsonify({'error': 'No fields to update'}), 400

    params.append(expense_id)
    c.execute(f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?", params)
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Expense updated'})


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    """Delete an expense."""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
    deleted = c.rowcount
    conn.commit()
    conn.close()

    if deleted == 0:
        return jsonify({'error': 'Expense not found'}), 404
    return jsonify({'success': True, 'message': 'Expense deleted'})


@app.route('/api/expenses/bulk-delete', methods=['POST'])
def bulk_delete():
    """Delete multiple expenses."""
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': 'No IDs provided'}), 400

    conn = get_db()
    c = conn.cursor()
    placeholders = ','.join('?' * len(ids))
    c.execute(f'DELETE FROM expenses WHERE id IN ({placeholders})', ids)
    count = c.rowcount
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'deleted': count})


# ─────────────── AI CATEGORIZATION ───────────────

@app.route('/api/ai/categorize', methods=['POST'])
def ai_categorize_endpoint():
    """Get AI category suggestion."""
    data = request.json
    description = data.get('description', '')

    category, confidence = ai_categorize(description)
    return jsonify({
        'category': category,
        'confidence': confidence,
        'suggestions': list(CATEGORY_KEYWORDS.keys())
    })


@app.route('/api/ai/insights', methods=['GET'])
def get_insights():
    """Get AI-powered spending insights."""
    days = request.args.get('days', 30, type=int)
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM expenses WHERE date >= ? ORDER BY date DESC', (since,))
    expenses = [dict(row) for row in c.fetchall()]
    conn.close()

    insights = ai_suggest_savings(expenses)

    return jsonify({
        'insights': insights,
        'period_days': days,
        'expense_count': len(expenses)
    })


# ─────────────── STATISTICS ───────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Comprehensive statistics."""
    conn = get_db()
    c = conn.cursor()

    # Overall totals
    c.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(AVG(amount), 0) FROM expenses')
    total_count, total_amount, avg_amount = c.fetchone()

    # Category breakdown
    c.execute('''SELECT category, SUM(amount) as total, COUNT(*) as count
                 FROM expenses GROUP BY category ORDER BY total DESC''')
    categories = [dict(row) for row in c.fetchall()]

    # Monthly breakdown (last 12 months)
    c.execute('''SELECT strftime('%Y-%m', date) as month,
                        SUM(amount) as total, COUNT(*) as count
                 FROM expenses
                 GROUP BY month ORDER BY month DESC LIMIT 12''')
    monthly = [dict(row) for row in c.fetchall()]

    # Daily breakdown (last 30 days)
    c.execute('''SELECT date, SUM(amount) as total, COUNT(*) as count
                 FROM expenses
                 WHERE date >= date('now', '-30 days')
                 GROUP BY date ORDER BY date ASC''')
    daily = [dict(row) for row in c.fetchall()]

    # Payment method breakdown
    c.execute('''SELECT payment_method, SUM(amount) as total, COUNT(*) as count
                 FROM expenses GROUP BY payment_method ORDER BY total DESC''')
    payment_methods = [dict(row) for row in c.fetchall()]

    # Top 5 largest expenses
    c.execute('''SELECT * FROM expenses ORDER BY amount DESC LIMIT 5''')
    top_expenses = [dict(row) for row in c.fetchall()]

    # This month vs last month
    this_month = datetime.now().strftime('%Y-%m')
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    c.execute('SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE strftime("%Y-%m", date) = ?',
              (this_month,))
    this_month_total = c.fetchone()[0]

    c.execute('SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE strftime("%Y-%m", date) = ?',
              (last_month,))
    last_month_total = c.fetchone()[0]

    change_pct = 0
    if last_month_total > 0:
        change_pct = ((this_month_total - last_month_total) / last_month_total) * 100

    conn.close()

    return jsonify({
        'total': {
            'count': total_count,
            'amount': round(total_amount, 2),
            'average': round(avg_amount, 2)
        },
        'categories': categories,
        'monthly': monthly,
        'daily': daily,
        'payment_methods': payment_methods,
        'top_expenses': top_expenses,
        'comparison': {
            'this_month': round(this_month_total, 2),
            'last_month': round(last_month_total, 2),
            'change_percent': round(change_pct, 2)
        }
    })


@app.route('/api/stats/category/<category>', methods=['GET'])
def get_category_stats(category):
    """Get stats for a specific category."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT COUNT(*), COALESCE(SUM(amount), 0), COALESCE(AVG(amount), 0)
                 FROM expenses WHERE category = ?''', (category,))
    count, total, avg = c.fetchone()

    c.execute('''SELECT strftime('%Y-%m', date) as month, SUM(amount) as total
                 FROM expenses WHERE category = ?
                 GROUP BY month ORDER BY month DESC LIMIT 12''', (category,))
    monthly = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify({
        'category': category,
        'count': count,
        'total': round(total, 2),
        'average': round(avg, 2),
        'monthly': monthly
    })


# ─────────────── BUDGETS ───────────────

@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    """Get all budgets with current spending."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM budgets')
    budgets = [dict(row) for row in c.fetchall()]

    this_month = datetime.now().strftime('%Y-%m')

    for budget in budgets:
        c.execute('''SELECT COALESCE(SUM(amount), 0) FROM expenses
                     WHERE category = ? AND strftime('%Y-%m', date) = ?''',
                  (budget['category'], this_month))
        spent = c.fetchone()[0]
        budget['spent'] = round(spent, 2)
        budget['remaining'] = round(budget['monthly_limit'] - spent, 2)
        budget['percent_used'] = round((spent / budget['monthly_limit']) * 100, 1) \
            if budget['monthly_limit'] > 0 else 0
        budget['status'] = (
            'over' if spent > budget['monthly_limit']
            else 'warning' if budget['percent_used'] > 80
            else 'good'
        )

    conn.close()
    return jsonify({'budgets': budgets})


@app.route('/api/budgets', methods=['POST'])
def set_budget():
    """Create or update a budget."""
    data = request.json
    category = data.get('category', '').strip()
    limit = data.get('monthly_limit')

    if not category or limit is None:
        return jsonify({'error': 'Category and monthly_limit required'}), 400

    try:
        limit = float(limit)
        if limit <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({'error': 'Valid limit required'}), 400

    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)
                 ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit''',
              (category, limit))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': f'Budget set for {category}'})


@app.route('/api/budgets/<category>', methods=['DELETE'])
def delete_budget(category):
    """Delete a budget."""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM budgets WHERE category = ?', (category,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/budgets/check', methods=['GET'])
def check_budget_alerts():
    """Check for budget alerts."""
    conn = get_db()
    c = conn.cursor()

    this_month = datetime.now().strftime('%Y-%m')
    c.execute('SELECT * FROM budgets')
    budgets = c.fetchall()

    alerts = []
    for budget in budgets:
        c.execute('''SELECT COALESCE(SUM(amount), 0) FROM expenses
                     WHERE category = ? AND strftime('%Y-%m', date) = ?''',
                  (budget['category'], this_month))
        spent = c.fetchone()[0]
        limit = budget['monthly_limit']
        pct = (spent / limit) * 100 if limit > 0 else 0

        if pct >= 100:
            alerts.append({
                'level': 'danger',
                'category': budget['category'],
                'message': f"🚨 OVER BUDGET on {budget['category']}! "
                           f"Spent ${spent:.2f} of ${limit:.2f}"
            })
        elif pct >= 80:
            alerts.append({
                'level': 'warning',
                'category': budget['category'],
                'message': f"⚠️ {budget['category']} at {pct:.0f}% "
                           f"(${spent:.2f}/${limit:.2f})"
            })

    conn.close()
    return jsonify({'alerts': alerts})


# ─────────────── CATEGORIES ───────────────

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM categories ORDER BY name')
    categories = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'categories': categories})


@app.route('/api/categories', methods=['POST'])
def add_category():
    """Add a new category."""
    data = request.json
    name = data.get('name', '').strip()
    icon = data.get('icon', '📦')
    color = data.get('color', '#667eea')

    if not name:
        return jsonify({'error': 'Name required'}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('INSERT INTO categories (name, icon, color) VALUES (?, ?, ?)',
                  (name, icon, color))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Category already exists'}), 400


# ─────────────── EXPORT / IMPORT ───────────────

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """Export all expenses to CSV."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM expenses ORDER BY date DESC')
    rows = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    if rows:
        writer.writerow(rows[0].keys())
        for row in rows:
            writer.writerow(tuple(row))

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = \
        f'attachment; filename=expenses_{datetime.now().strftime("%Y%m%d")}.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@app.route('/api/export/json', methods=['GET'])
def export_json():
    """Export all expenses to JSON."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM expenses ORDER BY date DESC')
    rows = [dict(row) for row in c.fetchall()]
    conn.close()

    response = make_response(json.dumps(rows, indent=2))
    response.headers['Content-Disposition'] = \
        f'attachment; filename=expenses_{datetime.now().strftime("%Y%m%d")}.json'
    response.headers['Content-Type'] = 'application/json'
    return response


# ─────────────── RECURRING EXPENSES ───────────────

@app.route('/api/recurring', methods=['GET'])
def get_recurring():
    """Get recurring expenses."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM expenses WHERE is_recurring = 1 ORDER BY date DESC')
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'recurring': rows})


@app.route('/api/recurring/process', methods=['POST'])
def process_recurring():
    """Process recurring expenses for current month."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM expenses WHERE is_recurring = 1')
    recurring = c.fetchall()

    current_month = datetime.now().strftime('%Y-%m')
    added = 0

    for exp in recurring:
        # Check if already added this month
        c.execute('''SELECT COUNT(*) FROM expenses
                     WHERE description = ? AND category = ?
                     AND strftime('%Y-%m', date) = ?
                     AND id != ?''',
                  (exp['description'], exp['category'], current_month, exp['id']))
        if c.fetchone()[0] == 0:
            today = datetime.now().strftime('%Y-%m-%d')
            c.execute('''INSERT INTO expenses
                         (description, amount, category, date, payment_method, notes, is_recurring)
                         VALUES (?, ?, ?, ?, ?, ?, 1)''',
                      (exp['description'], exp['amount'], exp['category'],
                       today, exp['payment_method'], exp['notes']))
            added += 1

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'added': added})


# ─────────────── SEARCH & FILTERS ───────────────

@app.route('/api/search', methods=['GET'])
def search_expenses():
    """Advanced search."""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'results': []})

    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT * FROM expenses
                 WHERE description LIKE ? OR notes LIKE ? OR category LIKE ?
                 ORDER BY date DESC LIMIT 50''',
              (f'%{query}%', f'%{query}%', f'%{query}%'))
    results = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify({'results': results, 'count': len(results)})


# ─────────────── HEALTH CHECK ───────────────

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })


# ═══════════════════════════════════════════════════════════════
#                    ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500


# ═══════════════════════════════════════════════════════════════
#                    MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    init_db()
    print("=" * 60)
    print("💰 AI Expense Manager v2.0")
    print("=" * 60)
    print("🌐 Server:     http://localhost:5000")
    print("📊 Dashboard:  http://localhost:5000")
    print("🔧 Health:     http://localhost:5000/api/health")
    print("=" * 60)
    app.run(debug=True, port=5000, host='0.0.0.0')