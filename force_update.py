import os
from index import app, db, User

# Ensure we are in the correct context
with app.app_context():
    try:
        # If it's SQLite, drop_all and create_all is simplest
        print("Starting Database Update...")
        db.drop_all()
        db.create_all()
        print("Database Update SUCCESSFUL!")
    except Exception as e:
        print(f"Update failed with: {e}")
