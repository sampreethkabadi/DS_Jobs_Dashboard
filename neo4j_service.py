import os
import logging
from collections import defaultdict
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self.uri = os.environ.get("NEO4J_URI", "")
        self.user = os.environ.get("NEO4J_USER", "")
        self.password = os.environ.get("NEO4J_PASSWORD", "")
        self.driver = None
        self._connected = False
        
    def connect(self):
        if self.uri and self.user and self.password:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                self.driver.verify_connectivity()
                self._connected = True
                logger.info("Connected to Neo4j database")
            except Exception as e:
                logger.warning(f"Could not connect to Neo4j: {e}")
                self._connected = False
        else:
            logger.info("Neo4j credentials not configured, using in-memory skill graph")
            self._connected = False
    
    def is_connected(self):
        return self._connected
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def add_skill(self, skill_name, category=None):
        return self.create_skill_node(skill_name, category)
    
    def create_skill_node(self, skill_name, category=None):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MERGE (s:Skill {name: $name})
            SET s.category = $category
            RETURN s
            """
            result = session.run(query, name=skill_name, category=category)
            return result.single()
    
    def add_role(self, role_name):
        return self.create_role_node(role_name)
    
    def create_role_node(self, role_name):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MERGE (r:Role {name: $name})
            RETURN r
            """
            result = session.run(query, name=role_name)
            return result.single()
    
    def add_industry(self, industry_name):
        return self.create_industry_node(industry_name)
    
    def create_industry_node(self, industry_name):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MERGE (i:Industry {name: $name})
            RETURN i
            """
            result = session.run(query, name=industry_name)
            return result.single()
    
    def add_location(self, location_name):
        return self.create_location_node(location_name)
    
    def create_location_node(self, location_name):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MERGE (l:Location {name: $name})
            RETURN l
            """
            result = session.run(query, name=location_name)
            return result.single()
    
    def add_role_skill(self, role_name, skill_name):
        return self.create_role_requires_skill(role_name, skill_name)
    
    def create_role_requires_skill(self, role_name, skill_name):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MATCH (r:Role {name: $role_name})
            MATCH (s:Skill {name: $skill_name})
            MERGE (r)-[rel:REQUIRES]->(s)
            ON CREATE SET rel.count = 1
            ON MATCH SET rel.count = rel.count + 1
            RETURN rel
            """
            result = session.run(query, role_name=role_name, skill_name=skill_name)
            return result.single()
    
    def add_industry_skill(self, industry_name, skill_name):
        return self.create_industry_uses_skill(industry_name, skill_name)
    
    def create_industry_uses_skill(self, industry_name, skill_name):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MATCH (i:Industry {name: $industry_name})
            MATCH (s:Skill {name: $skill_name})
            MERGE (i)-[rel:USES]->(s)
            ON CREATE SET rel.count = 1
            ON MATCH SET rel.count = rel.count + 1
            RETURN rel
            """
            result = session.run(query, industry_name=industry_name, skill_name=skill_name)
            return result.single()
    
    def add_location_role(self, location_name, role_name):
        return self.create_location_offers_role(location_name, role_name)
    
    def create_location_offers_role(self, location_name, role_name):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MATCH (l:Location {name: $location_name})
            MATCH (r:Role {name: $role_name})
            MERGE (l)-[rel:OFFERS]->(r)
            ON CREATE SET rel.count = 1
            ON MATCH SET rel.count = rel.count + 1
            RETURN rel
            """
            result = session.run(query, location_name=location_name, role_name=role_name)
            return result.single()
    
    def add_cooccurrence(self, skill1, skill2, job_id):
        return self.create_skill_cooccurrence(skill1, skill2, job_id)
    
    def create_skill_cooccurrence(self, skill1, skill2, job_id):
        if not self._connected:
            return None
        with self.driver.session() as session:
            query = """
            MATCH (s1:Skill {name: $skill1})
            MATCH (s2:Skill {name: $skill2})
            MERGE (s1)-[r:COOCCURS_WITH]-(s2)
            ON CREATE SET r.count = 1, r.jobs = [$job_id]
            ON MATCH SET r.count = r.count + 1, r.jobs = r.jobs + $job_id
            RETURN r
            """
            result = session.run(query, skill1=skill1, skill2=skill2, job_id=job_id)
            return result.single()
    
    def get_skill_cooccurrences(self, min_count=1):
        if not self._connected:
            return []
        with self.driver.session() as session:
            query = """
            MATCH (s1:Skill)-[r:COOCCURS_WITH]-(s2:Skill)
            WHERE r.count >= $min_count AND id(s1) < id(s2)
            RETURN s1.name as source, s2.name as target, r.count as weight
            ORDER BY r.count DESC
            """
            result = session.run(query, min_count=min_count)
            return [{"source": record["source"], "target": record["target"], "weight": record["weight"]} 
                    for record in result]
    
    def get_skill_nodes(self):
        if not self._connected:
            return []
        with self.driver.session() as session:
            query = """
            MATCH (s:Skill)
            OPTIONAL MATCH (s)-[r:COOCCURS_WITH]-()
            RETURN s.name as name, s.category as category, count(r) as connections
            """
            result = session.run(query)
            return [{"name": record["name"], "category": record["category"], "connections": record["connections"]} 
                    for record in result]
    
    def get_related_skills(self, skill_name, limit=10):
        if not self._connected:
            return []
        with self.driver.session() as session:
            query = """
            MATCH (s:Skill {name: $skill_name})-[r:COOCCURS_WITH]-(related:Skill)
            RETURN related.name as name, r.count as weight
            ORDER BY r.count DESC
            LIMIT $limit
            """
            result = session.run(query, skill_name=skill_name, limit=limit)
            return [{"name": record["name"], "weight": record["weight"]} for record in result]
    
    def get_full_graph(self, node_types=None, min_weight=1, limit_per_type=20):
        if not self._connected:
            return {"nodes": [], "links": []}
        if node_types is None:
            node_types = ["Skill", "Role", "Industry", "Location"]
        with self.driver.session() as session:
            type_filter = " OR ".join([f"n:{t}" for t in node_types])
            nodes_query = f"""
            MATCH (n)
            WHERE {type_filter}
            RETURN labels(n)[0] as type, n.name as name, n.category as category
            LIMIT {limit_per_type * len(node_types)}
            """
            nodes_result = session.run(nodes_query)
            nodes = [{"id": record["name"], "name": record["name"], 
                     "type": record["type"], "category": record.get("category")} 
                    for record in nodes_result]
            
            links_query = f"""
            MATCH (a)-[r]->(b)
            WHERE ({type_filter.replace('n:', 'a:')})
            AND ({type_filter.replace('n:', 'b:')})
            AND COALESCE(r.count, 1) >= {min_weight}
            RETURN a.name as source, b.name as target, type(r) as relationship, 
                   COALESCE(r.count, 1) as weight
            """
            links_result = session.run(links_query)
            links = [{"source": record["source"], "target": record["target"],
                     "relationship": record["relationship"], "weight": record["weight"]}
                    for record in links_result]
            
            return {"nodes": nodes, "links": links}
    
    def clear_all(self):
        if not self._connected:
            return
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")


class InMemorySkillGraph:
    def __init__(self):
        self.skills = {}
        self.roles = {}
        self.industries = {}
        self.locations = {}
        self.cooccurrences = defaultdict(lambda: defaultdict(int))
        self.role_skills = defaultdict(lambda: defaultdict(int))
        self.industry_skills = defaultdict(lambda: defaultdict(int))
        self.location_roles = defaultdict(lambda: defaultdict(int))
        self.skill_jobs = defaultdict(lambda: defaultdict(list))
    
    def add_skill(self, skill_name, category=None):
        if skill_name not in self.skills:
            self.skills[skill_name] = {"name": skill_name, "category": category, "connections": 0, "type": "Skill"}
    
    def add_role(self, role_name):
        if role_name not in self.roles:
            self.roles[role_name] = {"name": role_name, "type": "Role"}
    
    def add_industry(self, industry_name):
        if industry_name not in self.industries:
            self.industries[industry_name] = {"name": industry_name, "type": "Industry"}
    
    def add_location(self, location_name):
        if location_name not in self.locations:
            self.locations[location_name] = {"name": location_name, "type": "Location"}
    
    def add_role_skill(self, role_name, skill_name):
        self.role_skills[role_name][skill_name] += 1
    
    def add_industry_skill(self, industry_name, skill_name):
        self.industry_skills[industry_name][skill_name] += 1
    
    def add_location_role(self, location_name, role_name):
        self.location_roles[location_name][role_name] += 1
    
    def add_cooccurrence(self, skill1, skill2, job_id):
        if skill1 != skill2:
            key = tuple(sorted([skill1, skill2]))
            self.cooccurrences[key[0]][key[1]] += 1
            self.skill_jobs[key[0]][key[1]].append(job_id)
            self.skills[skill1]["connections"] = len(self.cooccurrences.get(skill1, {})) + \
                sum(1 for s in self.cooccurrences if skill1 in self.cooccurrences[s])
            self.skills[skill2]["connections"] = len(self.cooccurrences.get(skill2, {})) + \
                sum(1 for s in self.cooccurrences if skill2 in self.cooccurrences[s])
    
    def get_skill_nodes(self):
        return list(self.skills.values())
    
    def get_skill_cooccurrences(self, min_count=1):
        edges = []
        for skill1, targets in self.cooccurrences.items():
            for skill2, count in targets.items():
                if count >= min_count:
                    edges.append({"source": skill1, "target": skill2, "weight": count})
        return sorted(edges, key=lambda x: x["weight"], reverse=True)
    
    def get_related_skills(self, skill_name, limit=10):
        related = []
        for skill1, targets in self.cooccurrences.items():
            if skill1 == skill_name:
                for skill2, count in targets.items():
                    related.append({"name": skill2, "weight": count})
            elif skill_name in targets:
                related.append({"name": skill1, "weight": targets[skill_name]})
        return sorted(related, key=lambda x: x["weight"], reverse=True)[:limit]
    
    def get_full_graph(self, node_types=None, min_weight=1, limit_per_type=20):
        if node_types is None:
            node_types = ["Skill", "Role", "Industry", "Location"]
        
        nodes = []
        links = []
        node_ids = set()
        
        if "Role" in node_types:
            top_roles = sorted(self.roles.keys(), 
                             key=lambda r: sum(self.role_skills[r].values()), 
                             reverse=True)[:limit_per_type]
            for role in top_roles:
                nodes.append({"id": f"role_{role}", "name": role, "type": "Role", 
                            "count": sum(self.role_skills[role].values())})
                node_ids.add(f"role_{role}")
        
        if "Industry" in node_types:
            top_industries = sorted(self.industries.keys(),
                                  key=lambda i: sum(self.industry_skills[i].values()),
                                  reverse=True)[:limit_per_type]
            for industry in top_industries:
                nodes.append({"id": f"industry_{industry}", "name": industry, "type": "Industry",
                            "count": sum(self.industry_skills[industry].values())})
                node_ids.add(f"industry_{industry}")
        
        if "Location" in node_types:
            top_locations = sorted(self.locations.keys(),
                                 key=lambda l: sum(self.location_roles[l].values()),
                                 reverse=True)[:limit_per_type]
            for location in top_locations:
                nodes.append({"id": f"location_{location}", "name": location, "type": "Location",
                            "count": sum(self.location_roles[location].values())})
                node_ids.add(f"location_{location}")
        
        if "Skill" in node_types:
            skill_counts = {}
            for role, skills in self.role_skills.items():
                for skill, count in skills.items():
                    skill_counts[skill] = skill_counts.get(skill, 0) + count
            top_skills = sorted(skill_counts.keys(), 
                              key=lambda s: skill_counts[s], 
                              reverse=True)[:limit_per_type]
            for skill in top_skills:
                skill_info = self.skills.get(skill, {"category": "Other"})
                nodes.append({"id": f"skill_{skill}", "name": skill, "type": "Skill",
                            "category": skill_info.get("category", "Other"),
                            "count": skill_counts[skill]})
                node_ids.add(f"skill_{skill}")
        
        if "Role" in node_types and "Skill" in node_types:
            for role in top_roles if "Role" in node_types else []:
                for skill, count in self.role_skills[role].items():
                    if f"skill_{skill}" in node_ids and count >= min_weight:
                        links.append({
                            "source": f"role_{role}",
                            "target": f"skill_{skill}",
                            "relationship": "REQUIRES",
                            "weight": count
                        })
        
        if "Industry" in node_types and "Skill" in node_types:
            for industry in top_industries if "Industry" in node_types else []:
                for skill, count in self.industry_skills[industry].items():
                    if f"skill_{skill}" in node_ids and count >= min_weight:
                        links.append({
                            "source": f"industry_{industry}",
                            "target": f"skill_{skill}",
                            "relationship": "USES",
                            "weight": count
                        })
        
        if "Location" in node_types and "Role" in node_types:
            for location in top_locations if "Location" in node_types else []:
                for role, count in self.location_roles[location].items():
                    if f"role_{role}" in node_ids and count >= min_weight:
                        links.append({
                            "source": f"location_{location}",
                            "target": f"role_{role}",
                            "relationship": "OFFERS",
                            "weight": count
                        })
        
        return {"nodes": nodes, "links": links}
    
    def get_skills_for_role(self, role_name, limit=10):
        skills = self.role_skills.get(role_name, {})
        sorted_skills = sorted(skills.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"name": s, "count": c} for s, c in sorted_skills]
    
    def get_roles_for_skill(self, skill_name, limit=10):
        roles = []
        for role, skills in self.role_skills.items():
            if skill_name in skills:
                roles.append({"name": role, "count": skills[skill_name]})
        return sorted(roles, key=lambda x: x["count"], reverse=True)[:limit]
    
    def clear_all(self):
        self.skills = {}
        self.roles = {}
        self.industries = {}
        self.locations = {}
        self.cooccurrences = defaultdict(lambda: defaultdict(int))
        self.role_skills = defaultdict(lambda: defaultdict(int))
        self.industry_skills = defaultdict(lambda: defaultdict(int))
        self.location_roles = defaultdict(lambda: defaultdict(int))
        self.skill_jobs = defaultdict(lambda: defaultdict(list))


neo4j_service = Neo4jService()
in_memory_graph = InMemorySkillGraph()


def get_skill_graph():
    if neo4j_service.is_connected():
        return neo4j_service
    return in_memory_graph


def init_skill_graph():
    neo4j_service.connect()
    return get_skill_graph()
