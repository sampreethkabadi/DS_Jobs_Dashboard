import logging
from datetime import datetime
from itertools import combinations
from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import or_
from app import app, db
from models import Job, Skill
from neo4j_service import get_skill_graph, init_skill_graph, in_memory_graph
from sample_data import generate_sample_jobs, get_all_skills, SKILLS

logger = logging.getLogger(__name__)


def init_app():
    init_skill_graph()


@app.route('/')
def index():
    industry = request.args.get('industry', '')
    location = request.args.get('location', '')
    experience = request.args.get('experience', '')
    job_category = request.args.get('job_category', '')
    search = request.args.get('search', '')
    salary_min = request.args.get('salary_min', '', type=str)
    salary_max = request.args.get('salary_max', '', type=str)
    remote_ratio = request.args.get('remote_ratio', '')
    company_size = request.args.get('company_size', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25
    
    query = Job.query
    
    if search:
        query = query.filter(or_(
            Job.job_title.ilike(f'%{search}%'),
            Job.required_skills.ilike(f'%{search}%')
        ))
    if industry:
        query = query.filter(Job.industry == industry)
    if location:
        query = query.filter(Job.company_location == location)
    if experience:
        query = query.filter(Job.experience_level == experience)
    if job_category:
        query = query.filter(Job.job_category == job_category)
    if salary_min:
        try:
            query = query.filter(Job.salary_usd >= int(salary_min))
        except ValueError:
            pass
    if salary_max:
        try:
            query = query.filter(Job.salary_usd <= int(salary_max))
        except ValueError:
            pass
    if remote_ratio:
        query = query.filter(Job.remote_ratio == int(remote_ratio))
    if company_size:
        query = query.filter(Job.company_size == company_size)
    
    jobs = query.order_by(Job.posting_date.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    industries = db.session.query(Job.industry).distinct().order_by(Job.industry).all()
    locations = db.session.query(Job.company_location).distinct().order_by(Job.company_location).all()
    categories = db.session.query(Job.job_category).distinct().order_by(Job.job_category).all()
    
    salary_range = db.session.query(
        db.func.min(Job.salary_usd),
        db.func.max(Job.salary_usd)
    ).filter(Job.salary_usd.isnot(None)).first()
    min_salary = salary_range[0] or 0
    max_salary = salary_range[1] or 500000
    
    total_jobs = Job.query.count()
    avg_salary = db.session.query(db.func.avg(Job.salary_usd)).scalar() or 0
    total_skills = Skill.query.count()
    
    return render_template('index.html',
                         jobs=jobs,
                         industries=[i[0] for i in industries if i[0]],
                         locations=[l[0] for l in locations if l[0]],
                         categories=[c[0] for c in categories if c[0]],
                         selected_industry=industry,
                         selected_location=location,
                         selected_experience=experience,
                         selected_category=job_category,
                         selected_salary_min=salary_min,
                         selected_salary_max=salary_max,
                         selected_remote_ratio=remote_ratio,
                         selected_company_size=company_size,
                         min_salary=min_salary,
                         max_salary=max_salary,
                         search=search,
                         total_jobs=total_jobs,
                         avg_salary=int(avg_salary),
                         total_skills=total_skills)


@app.route('/job/new', methods=['GET', 'POST'])
def create_job():
    if request.method == 'POST':
        try:
            job = Job(
                job_id=f"JOB-{Job.query.count() + 1:05d}",
                job_title=request.form['job_title'],
                salary_usd=int(request.form.get('salary_usd', 0)) if request.form.get('salary_usd') else None,
                salary_currency=request.form.get('salary_currency', 'USD'),
                experience_level=request.form.get('experience_level'),
                employment_type=request.form.get('employment_type', 'FT'),
                job_category=request.form.get('job_category'),
                company_location=request.form.get('company_location'),
                company_size=request.form.get('company_size'),
                remote_ratio=int(request.form.get('remote_ratio', 0)),
                required_skills=request.form.get('required_skills', ''),
                education_required=request.form.get('education_required'),
                years_experience=int(request.form.get('years_experience', 0)) if request.form.get('years_experience') else None,
                industry=request.form.get('industry'),
                posting_date=datetime.strptime(request.form['posting_date'], '%Y-%m-%d') if request.form.get('posting_date') else datetime.now(),
                application_deadline=datetime.strptime(request.form['application_deadline'], '%Y-%m-%d') if request.form.get('application_deadline') else None,
                benefits_score=float(request.form.get('benefits_score', 5.0)) if request.form.get('benefits_score') else None
            )
            db.session.add(job)
            db.session.commit()
            
            update_skill_graph_for_job(job)
            
            flash('Job created successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating job: {str(e)}', 'error')
            logger.error(f"Error creating job: {e}")
    
    skills = Skill.query.all()
    return render_template('job_form.html', job=None, skills=skills, action='Create')


@app.route('/job/<int:job_id>/edit', methods=['GET', 'POST'])
def edit_job(job_id):
    job = Job.query.get_or_404(job_id)
    
    if request.method == 'POST':
        try:
            job.job_title = request.form['job_title']
            job.salary_usd = int(request.form.get('salary_usd', 0)) if request.form.get('salary_usd') else None
            job.salary_currency = request.form.get('salary_currency', 'USD')
            job.experience_level = request.form.get('experience_level')
            job.employment_type = request.form.get('employment_type', 'FT')
            job.job_category = request.form.get('job_category')
            job.company_location = request.form.get('company_location')
            job.company_size = request.form.get('company_size')
            job.remote_ratio = int(request.form.get('remote_ratio', 0))
            job.required_skills = request.form.get('required_skills', '')
            job.education_required = request.form.get('education_required')
            job.years_experience = int(request.form.get('years_experience', 0)) if request.form.get('years_experience') else None
            job.industry = request.form.get('industry')
            job.posting_date = datetime.strptime(request.form['posting_date'], '%Y-%m-%d') if request.form.get('posting_date') else job.posting_date
            job.application_deadline = datetime.strptime(request.form['application_deadline'], '%Y-%m-%d') if request.form.get('application_deadline') else None
            job.benefits_score = float(request.form.get('benefits_score', 5.0)) if request.form.get('benefits_score') else None
            
            db.session.commit()
            flash('Job updated successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating job: {str(e)}', 'error')
            logger.error(f"Error updating job: {e}")
    
    skills = Skill.query.all()
    return render_template('job_form.html', job=job, skills=skills, action='Update')


@app.route('/job/<int:job_id>/delete', methods=['POST'])
def delete_job(job_id):
    job = Job.query.get_or_404(job_id)
    try:
        db.session.delete(job)
        db.session.commit()
        flash('Job deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting job: {str(e)}', 'error')
    return redirect(url_for('index'))


@app.route('/job/<int:job_id>')
def view_job(job_id):
    job = Job.query.get_or_404(job_id)
    skills = job.get_skills_list()
    
    graph = get_skill_graph()
    related_skills = {}
    for skill in skills[:3]:
        related = graph.get_related_skills(skill, limit=5)
        if related:
            related_skills[skill] = related
    
    return render_template('job_detail.html', job=job, skills=skills, related_skills=related_skills)


@app.route('/visualizations')
def visualizations():
    return render_template('visualizations.html')


@app.route('/analytics')
def analytics():
    categories = db.session.query(Job.job_category).distinct().order_by(Job.job_category).all()
    categories = [c[0] for c in categories if c[0]]
    
    skills_by_category = {}
    for cat, skill_list in SKILLS.items():
        skills_by_category[cat] = skill_list
    
    return render_template('analytics.html',
                         categories=categories,
                         skills_by_category=skills_by_category)


@app.route('/api/skill-graph')
def api_skill_graph():
    graph = get_skill_graph()
    nodes = graph.get_skill_nodes()
    edges = graph.get_skill_cooccurrences(min_count=1)
    
    skill_counts = {}
    jobs = Job.query.all()
    for job in jobs:
        for skill in job.get_skills_list():
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    node_list = []
    for skill_name, count in skill_counts.items():
        category = None
        for cat, skills in SKILLS.items():
            if skill_name in skills:
                category = cat
                break
        node_list.append({
            "id": skill_name,
            "name": skill_name,
            "category": category or "Other",
            "count": count
        })
    
    return jsonify({
        "nodes": node_list,
        "links": edges
    })


@app.route('/api/skill-frequency')
def api_skill_frequency():
    industry = request.args.get('industry', '')
    experience = request.args.get('experience', '')
    
    query = Job.query
    if industry:
        query = query.filter(Job.industry == industry)
    if experience:
        query = query.filter(Job.experience_level == experience)
    
    jobs = query.all()
    skill_counts = {}
    
    for job in jobs:
        for skill in job.get_skills_list():
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:20]
    
    return jsonify({
        "labels": [s[0] for s in sorted_skills],
        "data": [s[1] for s in sorted_skills]
    })


@app.route('/api/salary-distribution')
def api_salary_distribution():
    group_by = request.args.get('group_by', 'location')
    
    if group_by == 'location':
        results = db.session.query(
            Job.company_location,
            db.func.avg(Job.salary_usd),
            db.func.min(Job.salary_usd),
            db.func.max(Job.salary_usd),
            db.func.count(Job.id)
        ).filter(Job.salary_usd.isnot(None)).group_by(Job.company_location).all()
        
        data = [{
            "label": r[0],
            "avg": round(r[1]) if r[1] else 0,
            "min": r[2] or 0,
            "max": r[3] or 0,
            "count": r[4]
        } for r in results if r[0]]
    else:
        results = db.session.query(
            Job.job_category,
            db.func.avg(Job.salary_usd),
            db.func.min(Job.salary_usd),
            db.func.max(Job.salary_usd),
            db.func.count(Job.id)
        ).filter(Job.salary_usd.isnot(None)).group_by(Job.job_category).all()
        
        data = [{
            "label": r[0],
            "avg": round(r[1]) if r[1] else 0,
            "min": r[2] or 0,
            "max": r[3] or 0,
            "count": r[4]
        } for r in results if r[0]]
    
    return jsonify(sorted(data, key=lambda x: x['avg'], reverse=True))


@app.route('/api/industry-skills')
def api_industry_skills():
    results = db.session.query(Job.industry, Job.required_skills).filter(
        Job.industry.isnot(None),
        Job.required_skills.isnot(None)
    ).all()
    
    industry_skills = {}
    for industry, skills_str in results:
        if industry not in industry_skills:
            industry_skills[industry] = {}
        for skill in [s.strip() for s in skills_str.split(',')]:
            industry_skills[industry][skill] = industry_skills[industry].get(skill, 0) + 1
    
    formatted = []
    for industry, skills in industry_skills.items():
        top_skills = sorted(skills.items(), key=lambda x: x[1], reverse=True)[:5]
        formatted.append({
            "industry": industry,
            "skills": [{"name": s[0], "count": s[1]} for s in top_skills]
        })
    
    return jsonify(sorted(formatted, key=lambda x: x['industry']))


@app.route('/api/skill-trends')
def api_skill_trends():
    jobs = Job.query.filter(Job.posting_date.isnot(None)).order_by(Job.posting_date).all()
    
    monthly_skills = {}
    for job in jobs:
        month_key = job.posting_date.strftime('%Y-%m')
        if month_key not in monthly_skills:
            monthly_skills[month_key] = {}
        for skill in job.get_skills_list():
            monthly_skills[month_key][skill] = monthly_skills[month_key].get(skill, 0) + 1
    
    all_skills_count = {}
    for job in jobs:
        for skill in job.get_skills_list():
            all_skills_count[skill] = all_skills_count.get(skill, 0) + 1
    top_skills = sorted(all_skills_count.items(), key=lambda x: x[1], reverse=True)[:10]
    skill_names = [s[0] for s in top_skills]
    
    months = sorted(monthly_skills.keys())
    datasets = []
    colors = ['#4f46e5', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6', '#ef4444', '#14b8a6', '#f97316', '#6366f1']
    
    for i, skill in enumerate(skill_names):
        data = []
        for month in months:
            data.append(monthly_skills.get(month, {}).get(skill, 0))
        datasets.append({
            "label": skill,
            "data": data,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)] + "20",
            "fill": False,
            "tension": 0.3
        })
    
    return jsonify({
        "labels": months,
        "datasets": datasets
    })


@app.route('/api/skill-recommender')
def api_skill_recommender():
    current_skills = request.args.get('skills', '')
    career_goal = request.args.get('career_goal', '')
    
    if not current_skills:
        return jsonify({"recommendations": [], "message": "Please select your current skills"})
    
    current_skill_list = [s.strip() for s in current_skills.split(',')]
    
    query = Job.query
    if career_goal:
        query = query.filter(Job.job_category == career_goal)
    
    jobs = query.all()
    
    skill_freq = {}
    skill_cooccur = {}
    
    for job in jobs:
        job_skills = job.get_skills_list()
        has_current = any(s in current_skill_list for s in job_skills)
        
        for skill in job_skills:
            skill_freq[skill] = skill_freq.get(skill, 0) + 1
            if has_current and skill not in current_skill_list:
                skill_cooccur[skill] = skill_cooccur.get(skill, 0) + 1
    
    recommendations = []
    for skill, count in skill_cooccur.items():
        relevance = count / max(skill_freq.get(skill, 1), 1)
        category = None
        for cat, cat_skills in SKILLS.items():
            if skill in cat_skills:
                category = cat
                break
        recommendations.append({
            "skill": skill,
            "frequency": count,
            "relevance": round(relevance * 100, 1),
            "category": category or "Other"
        })
    
    recommendations = sorted(recommendations, key=lambda x: (x['relevance'], x['frequency']), reverse=True)[:10]
    
    return jsonify({
        "recommendations": recommendations,
        "current_skills": current_skill_list,
        "career_goal": career_goal
    })


@app.route('/api/role-similarity')
def api_role_similarity():
    job_id = request.args.get('job_id', type=int)
    
    if not job_id:
        categories = db.session.query(Job.job_category).distinct().all()
        categories = [c[0] for c in categories if c[0]]
        
        category_similarities = {}
        for cat in categories:
            cat_jobs = Job.query.filter(Job.job_category == cat).all()
            cat_skills = set()
            for job in cat_jobs:
                cat_skills.update(job.get_skills_list())
            category_similarities[cat] = {
                "skills": list(cat_skills),
                "job_count": len(cat_jobs)
            }
        
        similarity_matrix = []
        for cat1 in categories:
            for cat2 in categories:
                if cat1 != cat2:
                    skills1 = set(category_similarities[cat1]["skills"])
                    skills2 = set(category_similarities[cat2]["skills"])
                    intersection = len(skills1 & skills2)
                    union = len(skills1 | skills2)
                    similarity = (intersection / union * 100) if union > 0 else 0
                    similarity_matrix.append({
                        "source": cat1,
                        "target": cat2,
                        "similarity": round(similarity, 1)
                    })
        
        return jsonify({
            "categories": category_similarities,
            "similarities": similarity_matrix
        })
    
    target_job = Job.query.get_or_404(job_id)
    target_skills = set(target_job.get_skills_list())
    
    similar_jobs = []
    all_jobs = Job.query.filter(Job.id != job_id).all()
    
    for job in all_jobs:
        job_skills = set(job.get_skills_list())
        intersection = len(target_skills & job_skills)
        union = len(target_skills | job_skills)
        similarity = (intersection / union * 100) if union > 0 else 0
        
        if similarity > 20:
            similar_jobs.append({
                "id": job.id,
                "title": job.job_title,
                "category": job.job_category,
                "location": job.company_location,
                "salary": job.salary_usd,
                "similarity": round(similarity, 1),
                "shared_skills": list(target_skills & job_skills),
                "unique_skills": list(job_skills - target_skills)
            })
    
    similar_jobs = sorted(similar_jobs, key=lambda x: x['similarity'], reverse=True)[:10]
    
    return jsonify({
        "target_job": target_job.to_dict(),
        "similar_jobs": similar_jobs
    })


@app.route('/api/industry-comparison')
def api_industry_comparison():
    industries = db.session.query(Job.industry).distinct().all()
    industries = [i[0] for i in industries if i[0]]
    
    all_jobs = Job.query.all()
    all_skills = set()
    for job in all_jobs:
        all_skills.update(job.get_skills_list())
    
    skill_categories = {}
    for skill in all_skills:
        for cat, cat_skills in SKILLS.items():
            if skill in cat_skills:
                skill_categories[skill] = cat
                break
    
    category_counts = {cat: 0 for cat in SKILLS.keys()}
    for skill in all_skills:
        cat = skill_categories.get(skill)
        if cat:
            category_counts[cat] += 1
    top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    radar_labels = [c[0] for c in top_categories]
    
    industry_data = {}
    for industry in industries:
        ind_jobs = [j for j in all_jobs if j.industry == industry]
        category_skill_count = {cat: 0 for cat in radar_labels}
        
        for job in ind_jobs:
            for skill in job.get_skills_list():
                cat = skill_categories.get(skill)
                if cat and cat in category_skill_count:
                    category_skill_count[cat] += 1
        
        total = sum(category_skill_count.values()) or 1
        normalized = {cat: round(count / total * 100, 1) for cat, count in category_skill_count.items()}
        industry_data[industry] = normalized
    
    colors = ['#4f46e5', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6', '#ef4444', '#14b8a6', '#f97316', '#6366f1']
    datasets = []
    for i, industry in enumerate(industries):
        datasets.append({
            "label": industry,
            "data": [industry_data[industry].get(cat, 0) for cat in radar_labels],
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)] + "30",
            "borderWidth": 2,
            "pointRadius": 3
        })
    
    return jsonify({
        "labels": radar_labels,
        "datasets": datasets
    })


@app.route('/api/relationship-graph')
def api_relationship_graph():
    node_types = request.args.get('types', 'Skill,Role').split(',')
    min_weight = request.args.get('min_weight', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    graph = get_skill_graph()
    
    if hasattr(graph, 'get_full_graph'):
        data = graph.get_full_graph(node_types=node_types, min_weight=min_weight, limit_per_type=limit)
        return jsonify(data)
    
    return jsonify({"nodes": [], "links": []})


@app.route('/init-data', methods=['POST'])
def init_data():
    try:
        Job.query.delete()
        Skill.query.delete()
        in_memory_graph.clear_all()
        
        skills_data = get_all_skills()
        for skill_data in skills_data:
            skill = Skill(name=skill_data['name'], category=skill_data['category'])
            db.session.add(skill)
            in_memory_graph.add_skill(skill_data['name'], skill_data['category'])
        
        jobs_data = generate_sample_jobs(2000)
        for job_data in jobs_data:
            job = Job(**job_data)
            db.session.add(job)
        
        db.session.commit()
        
        jobs = Job.query.all()
        for job in jobs:
            update_skill_graph_for_job(job)
        
        flash(f'Successfully loaded {len(jobs_data)} AI job postings from CSV!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error initializing data: {str(e)}', 'error')
        logger.error(f"Error initializing data: {e}")
    
    return redirect(url_for('index'))


def update_skill_graph_for_job(job):
    skills = job.get_skills_list()
    graph = get_skill_graph()
    
    role = job.job_category or job.job_title
    industry = job.industry
    location = job.company_location
    
    if hasattr(graph, 'add_role') and role:
        graph.add_role(role)
    if hasattr(graph, 'add_industry') and industry:
        graph.add_industry(industry)
    if hasattr(graph, 'add_location') and location:
        graph.add_location(location)
    
    for skill in skills:
        category = None
        for cat, cat_skills in SKILLS.items():
            if skill in cat_skills:
                category = cat
                break
        if hasattr(graph, 'add_skill'):
            graph.add_skill(skill, category or "Other")
        elif hasattr(graph, 'create_skill_node'):
            graph.create_skill_node(skill, category)
        
        if hasattr(graph, 'add_role_skill') and role:
            graph.add_role_skill(role, skill)
        if hasattr(graph, 'add_industry_skill') and industry:
            graph.add_industry_skill(industry, skill)
    
    if hasattr(graph, 'add_location_role') and location and role:
        graph.add_location_role(location, role)
    
    for skill1, skill2 in combinations(skills, 2):
        if hasattr(graph, 'add_cooccurrence'):
            graph.add_cooccurrence(skill1, skill2, job.job_id)
        elif hasattr(graph, 'create_skill_cooccurrence'):
            graph.create_skill_cooccurrence(skill1, skill2, job.job_id)
