from webapp.app import app, db
from webapp.models import User

with app.app_context():
    # Make all users admins for now, or just the main one. We will upgrade all existing users.
    users = User.query.all()
    for u in users:
        u.is_admin = True
    db.session.commit()
    print(f"Successfully upgraded {len(users)} user(s) to Admin.")
