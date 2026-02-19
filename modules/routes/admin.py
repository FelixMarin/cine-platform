# modules/routes/admin.py
"""
Blueprint de admin: /admin/manage
"""
import logging
from flask import Blueprint, session, render_template

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


def is_logged_in():
    return session.get("logged_in") is True


def is_admin():
    return session.get('user_role') == 'admin'


@admin_bp.route('/admin/manage')
def admin_manage():
    """Página de gestión de admin"""
    if not is_logged_in():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
    
    if not is_admin():
        return render_template("403.html"), 403
    
    return render_template("admin_panel.html")
