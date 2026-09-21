import streamlit as st
st.title("AI-Powered Task Knowledge Management System")
from app.database import Base, engine, SessionLocal
from app import models
from app.auth import hash_password
from app.config import settings
Base.metadata.create_all(bind=engine)
db = SessionLocal()
for role_name in [models.RoleName.admin, models.RoleName.user]:
    if not db.query(models.Role).filter(models.Role.name == role_name).first():
        db.add(models.Role(name=role_name))
db.commit()
admin_role = db.query(models.Role).filter(models.Role.name == models.RoleName.admin).first()
existing_admin = db.query(models.User).filter(models.User.email == settings.ADMIN_EMAIL).first()
if not existing_admin:
    admin = models.User(
        name="Administrator",
        email=settings.ADMIN_EMAIL,
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role_id=admin_role.id,
    )
    db.add(admin)
    db.commit()
    print(f"Created admin user: {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")
else:
    print("Admin user already exists.")
db.close()
print("Seed complete.")
