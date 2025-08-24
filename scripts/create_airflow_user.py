import os
from airflow import models, settings
from airflow.utils.session import provide_session
from sqlalchemy.exc import IntegrityError
from airflow.models.role import Role # Explicitly import Role

# Set your Airflow home directory
os.environ['AIRFLOW_HOME'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

@provide_session
def create_airflow_user_programmatically(session=None, username='admin', email='admin@example.com',
                                         firstname='Admin', lastname='User', password='admin', role_name='Admin'):
    """
    Creates a new Airflow user programmatically.
    """
    try:
        # Check if the specified role exists
        role = session.query(models.Role).filter_by(name=role_name).first()
        if not role:
            print(f"Error: Role '{role_name}' not found. Available roles:")
            for r in session.query(models.Role).all():
                print(f"- {r.name}")
            print("Please choose an existing role or create it first.")
            return

        # Check if user already exists to prevent IntegrityError
        existing_user = session.query(models.User).filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists. Skipping creation.")
            return

        # Create a new User object
        user = models.User(
            username=username,
            email=email,
            first_name=firstname,
            last_name=lastname,
            role=role,
        )
        # Set the password (Airflow handles hashing internally)
        user.set_password(password)

        # Add the user to the session and commit to the database
        session.add(user)
        session.commit()
        print(f"User '{username}' created successfully with role '{role_name}'.")

    except IntegrityError:
        session.rollback()
        print(f"Error: User '{username}' or email '{email}' might already exist (database integrity violation).")
    except Exception as e:
        session.rollback()
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Ensure Airflow settings are loaded before calling provide_session
    settings.configure_orm()
    create_airflow_user_programmatically(
        username='admin',
        email='admin@example.com',
        firstname='Admin',
        lastname='User',
        password='admin',
        role_name='Admin'
    )