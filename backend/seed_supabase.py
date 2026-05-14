from database import engine
from sqlalchemy.orm import sessionmaker
from models.job import Job

Session = sessionmaker(bind=engine)
db = Session()

jobs = [
    Job(id=1, title="Backend Engineer", department="Engineering", description="Build and maintain REST APIs using FastAPI and Python.", requirements="Python, FastAPI, PostgreSQL, Docker, 3+ years experience", status="open"),
    Job(id=2, title="Frontend Developer", department="Engineering", description="Build responsive UIs with Vue 3 and modern CSS.", requirements="Vue.js, TypeScript, Tailwind CSS, 2+ years experience", status="open"),
    Job(id=3, title="Full Stack Developer", department="Engineering", description="End-to-end web application development.", requirements="Python, JavaScript, React or Vue, SQL, Docker, 3+ years experience", status="open")
]

try:
    for j in jobs:
        # Avoid duplicate primary keys if they exist
        existing = db.query(Job).filter(Job.id == j.id).first()
        if not existing:
            db.add(j)
    db.commit()
    print("Successfully seeded jobs to Supabase!")
except Exception as e:
    print("Error seeding jobs:", e)
finally:
    db.close()
