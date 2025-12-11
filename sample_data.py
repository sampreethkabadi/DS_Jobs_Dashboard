import csv
import os
from datetime import datetime
from itertools import combinations

SKILLS = {
    "ML": ["Python", "TensorFlow", "PyTorch", "Deep Learning", "Computer Vision", "NLP", "R", "Statistics", "Mathematics"],
    "Data": ["SQL", "Spark", "Hadoop", "Tableau", "Data Visualization", "Scala", "ETL"],
    "Cloud": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Linux"],
    "LLM": ["Transformers", "BERT", "GPT"],
    "Engineering": ["Git", "Java", "REST APIs"],
    "MLOps": ["MLOps", "CI/CD", "Model Monitoring"]
}

CSV_FILE_PATH = "attached_assets/ai_job_dataset.csv"


def load_jobs_from_csv():
    jobs = []
    
    if not os.path.exists(CSV_FILE_PATH):
        return jobs
    
    with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            posting_date = None
            if row.get('posting_date'):
                try:
                    posting_date = datetime.strptime(row['posting_date'], '%Y-%m-%d').date()
                except ValueError:
                    posting_date = None
            
            application_deadline = None
            if row.get('application_deadline'):
                try:
                    application_deadline = datetime.strptime(row['application_deadline'], '%Y-%m-%d').date()
                except ValueError:
                    application_deadline = None
            
            salary_usd = None
            if row.get('salary_usd'):
                try:
                    salary_usd = int(row['salary_usd'])
                except ValueError:
                    salary_usd = None
            
            years_experience = None
            if row.get('years_experience'):
                try:
                    years_experience = int(row['years_experience'])
                except ValueError:
                    years_experience = None
            
            remote_ratio = 0
            if row.get('remote_ratio'):
                try:
                    remote_ratio = int(row['remote_ratio'])
                except ValueError:
                    remote_ratio = 0
            
            job_description_length = None
            if row.get('job_description_length'):
                try:
                    job_description_length = int(row['job_description_length'])
                except ValueError:
                    job_description_length = None
            
            benefits_score = None
            if row.get('benefits_score'):
                try:
                    benefits_score = float(row['benefits_score'])
                except ValueError:
                    benefits_score = None
            
            salary_local = None
            if salary_usd:
                salary_local = float(salary_usd)
            
            job = {
                "job_id": row.get('job_id', ''),
                "job_title": row.get('job_title', ''),
                "salary_usd": salary_usd,
                "salary_currency": row.get('salary_currency', 'USD'),
                "salary_local": salary_local,
                "experience_level": row.get('experience_level', ''),
                "employment_type": row.get('employment_type', 'FT'),
                "job_category": get_job_category_from_title(row.get('job_title', '')),
                "company_location": row.get('company_location', ''),
                "company_size": row.get('company_size', ''),
                "employee_residence": row.get('employee_residence', ''),
                "remote_ratio": remote_ratio,
                "required_skills": row.get('required_skills', ''),
                "education_required": row.get('education_required', ''),
                "years_experience": years_experience,
                "industry": row.get('industry', ''),
                "posting_date": posting_date,
                "application_deadline": application_deadline,
                "job_description_length": job_description_length,
                "benefits_score": benefits_score
            }
            jobs.append(job)
    
    return jobs


def get_job_category_from_title(job_title):
    title_lower = job_title.lower()
    
    if "machine learning" in title_lower or "ml " in title_lower:
        return "Machine Learning"
    elif "data scientist" in title_lower:
        return "Data Science"
    elif "data engineer" in title_lower:
        return "Data Engineering"
    elif "data analyst" in title_lower:
        return "Analytics"
    elif "nlp" in title_lower:
        return "NLP"
    elif "computer vision" in title_lower:
        return "Computer Vision"
    elif "research" in title_lower:
        return "AI Research"
    elif "architect" in title_lower:
        return "Architecture"
    elif "product manager" in title_lower:
        return "Product Management"
    elif "consultant" in title_lower:
        return "Consulting"
    elif "robotics" in title_lower or "autonomous" in title_lower:
        return "Robotics"
    elif "mlops" in title_lower or "ml ops" in title_lower:
        return "MLOps"
    elif "software" in title_lower:
        return "Software Engineering"
    elif "principal" in title_lower:
        return "Leadership"
    elif "specialist" in title_lower:
        return "AI Specialist"
    else:
        return "AI/ML"


def generate_sample_jobs(num_jobs=100):
    jobs = load_jobs_from_csv()
    if jobs:
        return jobs[:num_jobs] if len(jobs) > num_jobs else jobs
    return []


def get_all_skills():
    all_skills = []
    for category, skills in SKILLS.items():
        for skill in skills:
            all_skills.append({"name": skill, "category": category})
    
    jobs = load_jobs_from_csv()
    existing_skill_names = {s["name"] for s in all_skills}
    
    for job in jobs:
        if job.get("required_skills"):
            for skill in job["required_skills"].split(","):
                skill = skill.strip()
                if skill and skill not in existing_skill_names:
                    category = categorize_skill(skill)
                    all_skills.append({"name": skill, "category": category})
                    existing_skill_names.add(skill)
    
    return all_skills


def categorize_skill(skill):
    skill_lower = skill.lower()
    
    if skill_lower in ['python', 'tensorflow', 'pytorch', 'deep learning', 'computer vision', 'nlp', 'r', 'statistics', 'mathematics']:
        return "ML"
    elif skill_lower in ['sql', 'spark', 'hadoop', 'tableau', 'data visualization', 'scala']:
        return "Data"
    elif skill_lower in ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'linux']:
        return "Cloud"
    elif skill_lower in ['git', 'java']:
        return "Engineering"
    elif skill_lower in ['mlops']:
        return "MLOps"
    else:
        return "Other"


def calculate_skill_cooccurrences(jobs):
    cooccurrences = {}
    
    for job in jobs:
        skills = [s.strip() for s in job.get("required_skills", "").split(",")]
        for skill1, skill2 in combinations(skills, 2):
            key = tuple(sorted([skill1, skill2]))
            if key not in cooccurrences:
                cooccurrences[key] = {"source": key[0], "target": key[1], "weight": 0, "jobs": []}
            cooccurrences[key]["weight"] += 1
            cooccurrences[key]["jobs"].append(job["job_id"])
    
    return list(cooccurrences.values())
