"""
Flask web application to view IPO results with filtering and sorting.
"""
from flask import Flask, render_template, jsonify, request
from database.accessors import get_accessor

app = Flask(__name__)


@app.route('/')
def index():
    """Main page showing all users"""
    with get_accessor() as db:
        users = [user.model_dump() for user in db.reports.list_user_stats()]
    return render_template('index.html', users=users)


@app.route('/user/<int:user_id>')
def user_details(user_id):
    """User-specific results page"""
    with get_accessor() as db:
        user, results = db.reports.get_user_details(user_id)
        if not user:
            return "User not found", 404

    return render_template('user_details.html', user=user, results=[result.model_dump() for result in results])


@app.route('/companies')
def companies():
    """All companies/IPOs page"""
    with get_accessor() as db:
        companies = [company.model_dump() for company in db.reports.list_company_stats()]
    return render_template('companies.html', companies=companies)


@app.route('/applications')
def applications():
    """All IPO applications page"""
    user_id = request.args.get('user_id', type=int)
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')

    with get_accessor() as db:
        applications = [
            application.model_dump()
            for application in db.reports.list_applications(
                user_id=user_id,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        ]

    return render_template('applications.html', applications=applications)


@app.route('/applications/user/<int:user_id>')
def user_applications(user_id):
    """User-specific IPO applications page"""
    with get_accessor() as db:
        user, applications = db.reports.get_user_applications(user_id)
        if not user:
            return "User not found", 404

    return render_template(
        'user_applications.html',
        user=user,
        applications=[application.model_dump() for application in applications],
    )


@app.route('/company/<int:company_id>')
def company_details(company_id):
    """Company-specific results showing all users"""
    with get_accessor() as db:
        result, users = db.reports.get_company_details(company_id)
        if not result:
            return "Company not found", 404

    return render_template('company_details.html', company=result, users=[user.model_dump() for user in users])


@app.route('/api/results')
def api_results():
    """API endpoint for all results with filtering and sorting"""
    # Get query parameters
    user_id = request.args.get('user_id', type=int)
    company_id = request.args.get('company_id', type=int)
    sort_by = request.args.get('sort_by', 'applied_date')
    sort_order = request.args.get('sort_order', 'desc')

    with get_accessor() as db:
        results = db.reports.list_results(
            user_id=user_id,
            company_id=company_id,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    return jsonify([result.model_dump() for result in results])


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
