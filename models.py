from datetime import datetime
from app import db


class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(50), unique=True, nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    salary_usd = db.Column(db.Integer)
    salary_currency = db.Column(db.String(10))
    salary_local = db.Column(db.Float)
    experience_level = db.Column(db.String(10))
    employment_type = db.Column(db.String(10))
    job_category = db.Column(db.String(100))
    company_location = db.Column(db.String(100))
    company_size = db.Column(db.String(10))
    employee_residence = db.Column(db.String(100))
    remote_ratio = db.Column(db.Integer)
    required_skills = db.Column(db.Text)
    education_required = db.Column(db.String(100))
    years_experience = db.Column(db.Integer)
    industry = db.Column(db.String(100))
    posting_date = db.Column(db.Date)
    application_deadline = db.Column(db.Date)
    job_description_length = db.Column(db.Integer)
    benefits_score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_title': self.job_title,
            'salary_usd': self.salary_usd,
            'salary_currency': self.salary_currency,
            'salary_local': self.salary_local,
            'experience_level': self.experience_level,
            'employment_type': self.employment_type,
            'job_category': self.job_category,
            'company_location': self.company_location,
            'company_size': self.company_size,
            'employee_residence': self.employee_residence,
            'remote_ratio': self.remote_ratio,
            'required_skills': self.required_skills,
            'education_required': self.education_required,
            'years_experience': self.years_experience,
            'industry': self.industry,
            'posting_date': self.posting_date.isoformat() if self.posting_date else None,
            'application_deadline': self.application_deadline.isoformat() if self.application_deadline else None,
            'job_description_length': self.job_description_length,
            'benefits_score': self.benefits_score
        }

    def get_skills_list(self):
        if self.required_skills:
            return [s.strip() for s in self.required_skills.split(',')]
        return []


class Skill(db.Model):
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category
        }
