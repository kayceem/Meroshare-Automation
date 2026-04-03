"""
Flask web application to view IPO results with filtering and sorting.
"""
from flask import Flask, render_template, jsonify, request
from sqlalchemy import desc, asc
from database.database import get_db
from database.models import Result, User, UserResult

app = Flask(__name__)


@app.route('/')
def index():
    """Main page showing all users"""
    with get_db() as db:
        users = db.query(User).all()
        user_stats = []

        for user in users:
            # Count applications per user
            app_count = db.query(UserResult).filter(UserResult.user_id == user.id).count()
            # Count allotted shares
            allotted = db.query(UserResult).filter(
                UserResult.user_id == user.id,
                UserResult.received_kitta > 0
            ).count()

            user_stats.append({
                'id': user.id,
                'name': user.name,
                'boid': user.boid,
                'applications': app_count,
                'allotted': allotted
            })

    return render_template('index.html', users=user_stats)


@app.route('/user/<int:user_id>')
def user_details(user_id):
    """User-specific results page"""
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return "User not found", 404

        # Get all user results with company details
        results = db.query(UserResult, Result).join(
            Result, UserResult.result_id == Result.id
        ).filter(UserResult.user_id == user_id).all()

        results_data = []
        for user_result, result in results:
            results_data.append({
                'company_name': result.company_name,
                'script': result.script,
                'share_type': result.share_type_name,
                'applied_date': user_result.applied_date,
                'amount': user_result.amount,
                'received_kitta': user_result.received_kitta or 0,
                'status': user_result.value,
                'meroshare_remark': user_result.meroshare_remark,
                'reason_or_remark': user_result.reason_or_remark,
            })

    return render_template('user_details.html', user=user, results=results_data)


@app.route('/companies')
def companies():
    """All companies/IPOs page"""
    with get_db() as db:
        results = db.query(Result).all()

        companies_data = []
        for result in results:
            # Count total applications for this company
            total_apps = db.query(UserResult).filter(
                UserResult.result_id == result.id
            ).count()

            # Count allotted applications
            allotted_apps = db.query(UserResult).filter(
                UserResult.result_id == result.id,
                UserResult.received_kitta > 0
            ).count()

            companies_data.append({
                'id': result.id,
                'company_name': result.company_name,
                'script': result.script,
                'share_type': result.share_type_name,
                'total_applications': total_apps,
                'allotted': allotted_apps
            })

    return render_template('companies.html', companies=companies_data)


@app.route('/company/<int:company_id>')
def company_details(company_id):
    """Company-specific results showing all users"""
    with get_db() as db:
        result = db.query(Result).filter(Result.id == company_id).first()
        if not result:
            return "Company not found", 404

        # Get all user results for this company
        user_results = db.query(UserResult, User).join(
            User, UserResult.user_id == User.id
        ).filter(UserResult.result_id == company_id).all()

        users_data = []
        for user_result, user in user_results:
            users_data.append({
                'user_name': user.name,
                'boid': user.boid,
                'applied_date': user_result.applied_date,
                'amount': user_result.amount,
                'received_kitta': user_result.received_kitta or 0,
                'status': user_result.value,
                'meroshare_remark': user_result.meroshare_remark,
                'reason_or_remark': user_result.reason_or_remark,
            })

    return render_template('company_details.html', company=result, users=users_data)


@app.route('/api/results')
def api_results():
    """API endpoint for all results with filtering and sorting"""
    # Get query parameters
    user_id = request.args.get('user_id', type=int)
    company_id = request.args.get('company_id', type=int)
    sort_by = request.args.get('sort_by', 'applied_date')
    sort_order = request.args.get('sort_order', 'desc')

    with get_db() as db:
        query = db.query(UserResult, Result, User).join(
            Result, UserResult.result_id == Result.id
        ).join(User, UserResult.user_id == User.id)

        # Apply filters
        if user_id:
            query = query.filter(UserResult.user_id == user_id)
        if company_id:
            query = query.filter(UserResult.result_id == company_id)

        # Apply sorting
        if sort_order == 'desc':
            if sort_by == 'company_name':
                query = query.order_by(desc(Result.company_name))
            elif sort_by == 'user_name':
                query = query.order_by(desc(User.name))
            elif sort_by == 'received_kitta':
                query = query.order_by(desc(UserResult.received_kitta))
            else:
                query = query.order_by(desc(UserResult.applied_date))
        else:
            if sort_by == 'company_name':
                query = query.order_by(asc(Result.company_name))
            elif sort_by == 'user_name':
                query = query.order_by(asc(User.name))
            elif sort_by == 'received_kitta':
                query = query.order_by(asc(UserResult.received_kitta))
            else:
                query = query.order_by(asc(UserResult.applied_date))

        results = query.all()

        results_data = []
        for user_result, result, user in results:
            results_data.append({
                'user_name': user.name,
                'boid': user.boid,
                'company_name': result.company_name,
                'script': result.script,
                'share_type': result.share_type_name,
                'applied_date': user_result.applied_date,
                'amount': user_result.amount,
                'received_kitta': user_result.received_kitta or 0,
                'status': user_result.value,
                'meroshare_remark': user_result.meroshare_remark,
            })

    return jsonify(results_data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
