from index import app, db
import os

with app.app_context():
    try:
        # Drop and recreate (The Nuke approach)
        print("Starting Database Rebuild...")
        db.drop_all()
        db.create_all()
        print("Success! Database has been rebuilt with VIP columns.")
    except Exception as e:
        print(f"Error: {e}")
