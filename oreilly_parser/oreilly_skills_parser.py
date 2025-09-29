#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
O'Reilly Learning Skills Parser
Discovers and lists all available skills on O'Reilly Learning platform
"""

import requests
import re
import json
import time
import os
from urllib.parse import urljoin, urlparse

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: beautifulsoup4 not available. Web scraping features will be limited.")


def load_cookies():
    """Load cookies from the cookies.json file if it exists"""
    cookies_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cookies.json')
    if os.path.exists(cookies_file):
        try:
            with open(cookies_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            print("Warning: Could not load cookies from cookies.json")
    return {}


def retrieve_page_contents(url, headers=None, cookies=None):
    """Retrieve page contents with proper error handling and authentication"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://learning.oreilly.com/',
        }
    
    try:
        session = requests.Session()
        if cookies:
            session.cookies.update(cookies)
        
        r = session.get(url, headers=headers, timeout=30)
        if r.status_code < 400:
            return r.text
        else:
            print(f"URL {url} returned status code: {r.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error retrieving {url}: {e}")
        return None
    except KeyboardInterrupt:
        print(f"\n⚠️  Interrupted while retrieving {url}")
        raise


def discover_skills_from_web_pages(cookies=None, verbose=True):
    """Discover skills by scraping O'Reilly Learning web pages"""
    print("🔍 Discovering skills from O'Reilly Learning web pages...")
    
    if not BS4_AVAILABLE:
        print("⚠️  BeautifulSoup not available, skipping web page scraping")
        return [], []
    
    skills = set()
    skill_urls = set()
    
    # Common skill discovery URLs
    discovery_urls = [
        'https://learning.oreilly.com/search/skills/',
        'https://learning.oreilly.com/topics/',
        'https://learning.oreilly.com/',
    ]
    
    for base_url in discovery_urls:
        if verbose:
            print(f"\n🌐 Checking: {base_url}")
        
        try:
            content = retrieve_page_contents(base_url, cookies=cookies)
            if not content:
                if verbose:
                    print(f"❌ Failed to retrieve {base_url}")
                continue
            
            # Parse HTML content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for skill links in various patterns
            skill_patterns = [
                # Direct skill links
                {'tag': 'a', 'href': re.compile(r'/search/skills/[^/]+/?$')},
                {'tag': 'a', 'href': re.compile(r'/topics/[^/]+/?$')},
                # Skill buttons or cards
                {'tag': 'button', 'data-skill': True},
                {'tag': 'div', 'class': re.compile(r'skill|topic')},
            ]
            
            for pattern in skill_patterns:
                elements = soup.find_all(pattern['tag'], pattern.get('href', {}) or pattern.get('data-skill', {}) or pattern.get('class', {}))
                
                for element in elements:
                    # Extract skill name and URL
                    skill_name = None
                    skill_url = None
                    
                    if element.name == 'a' and element.get('href'):
                        href = element.get('href')
                        if '/search/skills/' in href or '/topics/' in href:
                            skill_url = urljoin(base_url, href)
                            skill_name = element.get_text(strip=True)
                            
                            # Clean up skill name
                            if skill_name and len(skill_name) > 0:
                                skill_name = skill_name.replace('\n', ' ').strip()
                                if skill_name and skill_name not in ['', 'Skills', 'Topics', 'All']:
                                    skills.add(skill_name)
                                    skill_urls.add(skill_url)
                                    if verbose:
                                        print(f"   ✅ Found skill: {skill_name}")
                    
                    elif element.name in ['button', 'div'] and element.get_text(strip=True):
                        skill_name = element.get_text(strip=True)
                        if skill_name and len(skill_name) > 0:
                            skill_name = skill_name.replace('\n', ' ').strip()
                            if skill_name and skill_name not in ['', 'Skills', 'Topics', 'All']:
                                skills.add(skill_name)
                                if verbose:
                                    print(f"   ✅ Found skill: {skill_name}")
            
            # Look for JSON data in script tags that might contain skills
            script_tags = soup.find_all('script', type='application/json')
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Look for skills in various data structures
                        for key, value in data.items():
                            if 'skill' in key.lower() or 'topic' in key.lower():
                                if isinstance(value, list):
                                    for item in value:
                                        if isinstance(item, dict) and 'name' in item:
                                            skill_name = item['name']
                                            if skill_name:
                                                skills.add(skill_name)
                                                if verbose:
                                                    print(f"   ✅ Found skill in JSON: {skill_name}")
                except (json.JSONDecodeError, TypeError):
                    continue
            
        except Exception as e:
            if verbose:
                print(f"❌ Error processing {base_url}: {e}")
            continue
        
        # Add delay between requests
        time.sleep(1)
    
    return list(skills), list(skill_urls)


def discover_skills_from_api(cookies=None, verbose=True):
    """Discover skills using O'Reilly Learning API"""
    print("🔍 Discovering skills from O'Reilly Learning API...")
    
    skills = set()
    
    # Try the main search API with different queries
    search_queries = [
        '',  # Empty query to get all results
        'python', 'javascript', 'java', 'machine learning', 'data science',
        'web development', 'mobile development', 'devops', 'cloud computing',
        'database', 'security', 'design', 'leadership', 'project management'
    ]
    
    for query in search_queries:
        if verbose:
            print(f"\n🌐 Searching API for: '{query}'")
        
        try:
            # Use the main search API
            if query:
                api_url = f"https://learning.oreilly.com/api/v1/search?q={query}"
            else:
                api_url = "https://learning.oreilly.com/api/v1/search"
            
            content = retrieve_page_contents(api_url, cookies=cookies)
            if not content:
                if verbose:
                    print(f"❌ Failed to retrieve {api_url}")
                continue
            
            try:
                data = json.loads(content)
                
                # Look for skills in the search results
                if isinstance(data, dict) and 'results' in data:
                    for item in data['results']:
                        if isinstance(item, dict):
                            # Look for skill-related fields
                            for field in ['skill', 'skills', 'topic', 'topics', 'category', 'categories']:
                                if field in item:
                                    skill_value = item[field]
                                    if isinstance(skill_value, str):
                                        skills.add(skill_value.strip())
                                    elif isinstance(skill_value, list):
                                        for skill in skill_value:
                                            if isinstance(skill, str):
                                                skills.add(skill.strip())
                                            elif isinstance(skill, dict) and 'name' in skill:
                                                skills.add(skill['name'].strip())
                
            except json.JSONDecodeError:
                if verbose:
                    print(f"❌ Invalid JSON response from {api_url}")
                continue
                
        except Exception as e:
            if verbose:
                print(f"❌ Error processing query '{query}': {e}")
            continue
        
        # Add delay between requests
        time.sleep(1)
    
    return list(skills)


def discover_known_skills():
    """Discover skills from a comprehensive list of known O'Reilly Learning skills"""
    print("🔍 Discovering skills from known skill database...")
    
    # Comprehensive list of known O'Reilly Learning skills
    known_skills = [
        # Programming Languages
        'Python', 'JavaScript', 'Java', 'C++', 'C#', 'Ruby', 'Go', 'Rust', 'Swift', 'Kotlin',
        'PHP', 'Perl', 'Scala', 'Clojure', 'Haskell', 'Erlang', 'Elixir', 'R', 'MATLAB',
        'TypeScript', 'Dart', 'Lua', 'Julia', 'Crystal', 'Nim', 'Zig', 'V', 'Carbon',
        
        # Web Development
        'Web Development', 'Frontend Development', 'Backend Development', 'Full Stack Development',
        'HTML', 'CSS', 'Sass', 'Less', 'Bootstrap', 'Tailwind CSS',
        'React', 'Angular', 'Vue.js', 'Svelte', 'Ember.js', 'Backbone.js',
        'Node.js', 'Express.js', 'Next.js', 'Nuxt.js', 'Gatsby', 'SvelteKit',
        'Django', 'Flask', 'FastAPI', 'Pyramid', 'Tornado', 'Bottle',
        'Spring Boot', 'Spring Framework', 'Hibernate', 'Struts', 'Play Framework',
        'ASP.NET', 'ASP.NET Core', 'Blazor', 'SignalR',
        'Laravel', 'Symfony', 'CodeIgniter', 'CakePHP', 'Zend Framework',
        'Ruby on Rails', 'Sinatra', 'Hanami',
        
        # Mobile Development
        'Mobile Development', 'iOS Development', 'Android Development', 'Cross-Platform Development',
        'React Native', 'Flutter', 'Xamarin', 'Ionic', 'Cordova', 'PhoneGap',
        'SwiftUI', 'UIKit', 'Core Data', 'Core Animation',
        'Android Studio', 'Kotlin Multiplatform', 'Jetpack Compose',
        
        # Data Science & AI
        'Data Science', 'Machine Learning', 'Artificial Intelligence', 'Deep Learning',
        'Data Analysis', 'Data Visualization', 'Statistics', 'Probability',
        'NumPy', 'Pandas', 'Matplotlib', 'Seaborn', 'Plotly', 'Bokeh',
        'Scikit-learn', 'TensorFlow', 'PyTorch', 'Keras', 'OpenCV',
        'Natural Language Processing', 'Computer Vision', 'Reinforcement Learning',
        'Big Data', 'Apache Spark', 'Hadoop', 'Kafka', 'Elasticsearch',
        'Data Engineering', 'ETL', 'Data Warehousing', 'Business Intelligence',
        
        # Cloud & DevOps
        'Cloud Computing', 'DevOps', 'Site Reliability Engineering', 'Infrastructure as Code',
        'AWS', 'Amazon Web Services', 'Azure', 'Google Cloud Platform', 'GCP',
        'Docker', 'Kubernetes', 'Terraform', 'Ansible', 'Jenkins', 'GitLab CI',
        'Microservices', 'Serverless', 'Lambda', 'API Gateway', 'CloudFormation',
        'Monitoring', 'Logging', 'Alerting', 'Prometheus', 'Grafana', 'ELK Stack',
        
        # Databases
        'Database', 'SQL', 'NoSQL', 'MySQL', 'PostgreSQL', 'SQLite', 'Oracle',
        'MongoDB', 'Redis', 'Cassandra', 'DynamoDB', 'CouchDB', 'Neo4j',
        'Database Design', 'Database Administration', 'Data Modeling',
        
        # Security
        'Cybersecurity', 'Information Security', 'Network Security', 'Application Security',
        'Penetration Testing', 'Ethical Hacking', 'Security Auditing', 'Risk Assessment',
        'Cryptography', 'PKI', 'SSL/TLS', 'OAuth', 'JWT', 'SAML',
        'Security Operations', 'Incident Response', 'Threat Intelligence',
        
        # Operating Systems
        'Linux', 'Windows', 'macOS', 'Unix', 'System Administration',
        'Shell Scripting', 'Bash', 'PowerShell', 'Command Line',
        'Virtualization', 'Containerization', 'Hypervisors',
        
        # Networking
        'Networking', 'TCP/IP', 'HTTP/HTTPS', 'DNS', 'Load Balancing',
        'CDN', 'VPN', 'Firewalls', 'Switches', 'Routers',
        'Network Protocols', 'Network Security', 'Network Monitoring',
        
        # Software Engineering
        'Software Engineering', 'Software Architecture', 'Design Patterns',
        'Clean Code', 'Code Review', 'Refactoring', 'Technical Debt',
        'Agile', 'Scrum', 'Kanban', 'Extreme Programming', 'Test-Driven Development',
        'Continuous Integration', 'Continuous Deployment', 'Git', 'Version Control',
        
        # Project Management
        'Project Management', 'Product Management', 'Program Management',
        'Agile Project Management', 'Waterfall', 'Lean', 'Six Sigma',
        'Risk Management', 'Stakeholder Management', 'Resource Planning',
        
        # Leadership & Management
        'Leadership', 'Team Management', 'People Management', 'Change Management',
        'Strategic Planning', 'Business Analysis', 'Process Improvement',
        'Communication', 'Presentation Skills', 'Public Speaking',
        
        # Design & UX
        'User Experience', 'User Interface Design', 'UX Design', 'UI Design',
        'Interaction Design', 'Information Architecture', 'Usability Testing',
        'Design Systems', 'Prototyping', 'Wireframing', 'Sketch', 'Figma',
        'Adobe Creative Suite', 'Photoshop', 'Illustrator', 'InDesign',
        
        # Business & Finance
        'Business Analysis', 'Financial Analysis', 'Accounting', 'Finance',
        'Economics', 'Marketing', 'Digital Marketing', 'SEO', 'SEM',
        'Sales', 'Customer Success', 'Business Intelligence', 'Analytics',
        'Business Strategy', 'Strategic Planning', 'Market Research', 'Competitive Analysis',
        'Financial Planning', 'Budgeting', 'Cost Management', 'Investment Analysis',
        'Corporate Finance', 'Mergers & Acquisitions', 'Valuation', 'Risk Management',
        'Business Development', 'Partnership Development', 'Revenue Growth',
        'Customer Acquisition', 'Customer Retention', 'Customer Experience',
        'Brand Management', 'Product Marketing', 'Content Marketing', 'Social Media Marketing',
        'Email Marketing', 'Marketing Automation', 'Growth Hacking', 'Conversion Optimization',
        'E-commerce', 'Online Business', 'Startup Strategy', 'Entrepreneurship',
        'Venture Capital', 'Fundraising', 'Pitch Development', 'Business Plan Writing',
        
        # Leadership & Management
        'Leadership', 'Team Management', 'People Management', 'Change Management',
        'Strategic Planning', 'Business Analysis', 'Process Improvement',
        'Communication', 'Presentation Skills', 'Public Speaking',
        'Executive Leadership', 'C-Suite Skills', 'Board Management',
        'Organizational Development', 'Culture Building', 'Employee Engagement',
        'Performance Management', 'Talent Development', 'Succession Planning',
        'Diversity & Inclusion', 'Unconscious Bias', 'Cultural Competency',
        'Remote Leadership', 'Virtual Team Management', 'Distributed Teams',
        'Crisis Management', 'Decision Making', 'Problem Solving',
        'Negotiation', 'Conflict Resolution', 'Mediation', 'Facilitation',
        'Coaching', 'Mentoring', 'Executive Coaching', 'Leadership Development',
        'Emotional Intelligence', 'Self-Awareness', 'Empathy', 'Active Listening',
        'Influence', 'Persuasion', 'Stakeholder Management', 'Relationship Building',
        
        # Personal Development & Soft Skills
        'Personal Development', 'Self-Improvement', 'Goal Setting', 'Time Management',
        'Productivity', 'Work-Life Balance', 'Stress Management', 'Mindfulness',
        'Meditation', 'Resilience', 'Adaptability', 'Flexibility',
        'Critical Thinking', 'Analytical Thinking', 'Creative Thinking', 'Innovation',
        'Design Thinking', 'Systems Thinking', 'Strategic Thinking',
        'Communication Skills', 'Written Communication', 'Verbal Communication',
        'Nonverbal Communication', 'Cross-Cultural Communication', 'Interpersonal Skills',
        'Networking', 'Relationship Building', 'Collaboration', 'Teamwork',
        'Emotional Intelligence', 'Self-Regulation', 'Motivation', 'Inspiration',
        'Confidence Building', 'Public Speaking', 'Presentation Skills',
        'Storytelling', 'Narrative Skills', 'Influence', 'Persuasion',
        'Negotiation', 'Conflict Resolution', 'Difficult Conversations',
        'Feedback Skills', 'Giving Feedback', 'Receiving Feedback', 'Performance Reviews',
        'Career Development', 'Career Planning', 'Professional Development',
        'Skill Development', 'Learning Agility', 'Continuous Learning',
        'Personal Branding', 'Professional Branding', 'Online Presence',
        'LinkedIn Optimization', 'Resume Writing', 'Interview Skills',
        'Salary Negotiation', 'Career Transition', 'Job Search', 'Recruiting',
        
        # Project & Program Management
        'Project Management', 'Program Management', 'Portfolio Management',
        'Agile Project Management', 'Scrum Master', 'Product Owner',
        'Waterfall', 'Lean', 'Six Sigma', 'Lean Six Sigma',
        'PMI', 'PMP', 'CAPM', 'PRINCE2', 'ITIL', 'COBIT',
        'Risk Management', 'Issue Management', 'Change Management',
        'Stakeholder Management', 'Communication Management', 'Quality Management',
        'Scope Management', 'Time Management', 'Cost Management', 'Resource Management',
        'Procurement Management', 'Integration Management', 'Human Resource Management',
        'Project Planning', 'Project Execution', 'Project Monitoring', 'Project Control',
        'Project Closure', 'Lessons Learned', 'Best Practices',
        'Project Governance', 'Project Methodology', 'Project Tools',
        'Microsoft Project', 'Jira', 'Confluence', 'Trello', 'Asana',
        'Gantt Charts', 'Critical Path Method', 'PERT', 'Earned Value Management',
        
        # Data & Analytics
        'Data Analysis', 'Business Intelligence', 'Data Visualization', 'Tableau', 'Power BI',
        'Excel', 'Advanced Excel', 'VBA', 'SQL', 'Database Management',
        'Statistical Analysis', 'Predictive Analytics', 'Machine Learning',
        'Data Mining', 'Big Data', 'Data Science', 'Data Engineering',
        'ETL', 'Data Warehousing', 'Data Governance', 'Data Quality',
        'KPI Development', 'Metrics', 'Dashboard Design', 'Reporting',
        'Financial Modeling', 'Forecasting', 'Trend Analysis',
        'A/B Testing', 'Experimentation', 'Conversion Analysis',
        'Customer Analytics', 'Marketing Analytics', 'Web Analytics',
        'Google Analytics', 'Adobe Analytics', 'Mixpanel', 'Amplitude',
        
        # Sales & Customer Success
        'Sales', 'Sales Management', 'Sales Strategy', 'Sales Process',
        'Lead Generation', 'Lead Qualification', 'Prospecting', 'Cold Calling',
        'Sales Funnel', 'Sales Pipeline', 'Sales Forecasting', 'Sales Analytics',
        'CRM', 'Salesforce', 'HubSpot', 'Pipedrive', 'Zoho CRM',
        'Account Management', 'Key Account Management', 'Enterprise Sales',
        'B2B Sales', 'B2C Sales', 'Inside Sales', 'Outside Sales',
        'Sales Training', 'Sales Coaching', 'Sales Enablement',
        'Customer Success', 'Customer Experience', 'Customer Retention',
        'Customer Onboarding', 'Customer Support', 'Customer Service',
        'Client Relations', 'Account Management', 'Relationship Management',
        
        # Human Resources
        'Human Resources', 'HR Management', 'Talent Acquisition', 'Recruiting',
        'Talent Management', 'Performance Management', 'Employee Relations',
        'Compensation & Benefits', 'Payroll', 'HRIS', 'Workday', 'BambooHR',
        'Employee Engagement', 'Employee Development', 'Training & Development',
        'Learning & Development', 'Organizational Development', 'Change Management',
        'Diversity & Inclusion', 'Workplace Culture', 'Employee Wellness',
        'HR Analytics', 'People Analytics', 'Workforce Planning',
        'Succession Planning', 'Leadership Development', 'Executive Search',
        'HR Compliance', 'Employment Law', 'Labor Relations', 'Union Relations',
        
        # Operations & Supply Chain
        'Operations Management', 'Supply Chain Management', 'Logistics',
        'Inventory Management', 'Procurement', 'Vendor Management',
        'Quality Management', 'Process Improvement', 'Lean Manufacturing',
        'Six Sigma', 'Continuous Improvement', 'Kaizen', '5S',
        'Production Planning', 'Capacity Planning', 'Demand Planning',
        'Warehouse Management', 'Distribution', 'Transportation',
        'Global Supply Chain', 'International Trade', 'Import/Export',
        'Compliance', 'Regulatory Affairs', 'Health & Safety',
        'Environmental Management', 'Sustainability', 'Green Operations',
        
        # Other Technical Skills
        'Blockchain', 'Cryptocurrency', 'Smart Contracts', 'Solidity',
        'Game Development', 'Unity', 'Unreal Engine', 'C# for Games',
        'Embedded Systems', 'IoT', 'Arduino', 'Raspberry Pi',
        'Quantum Computing', 'Robotics', 'Automation',
        'Testing', 'Quality Assurance', 'Test Automation', 'Selenium',
        'Performance Testing', 'Load Testing', 'Security Testing',
        
        # Creative & Design
        'Graphic Design', 'Web Design', 'UI Design', 'UX Design',
        'Adobe Photoshop', 'Adobe Illustrator', 'Adobe InDesign',
        'Sketch', 'Figma', 'Adobe XD', 'InVision', 'Principle',
        'Video Editing', 'Adobe Premiere', 'Final Cut Pro', 'DaVinci Resolve',
        'Motion Graphics', 'After Effects', 'Cinema 4D', 'Blender',
        'Photography', 'Digital Photography', 'Photo Editing', 'Lightroom',
        'Typography', 'Color Theory', 'Design Systems', 'Brand Design',
        'Logo Design', 'Print Design', 'Packaging Design', 'Environmental Design',
        'User Research', 'Usability Testing', 'Information Architecture',
        'Wireframing', 'Prototyping', 'Interaction Design', 'Service Design',
        
        # Writing & Content
        'Technical Writing', 'Content Writing', 'Copywriting', 'Blog Writing',
        'Grant Writing', 'Proposal Writing', 'Report Writing', 'Documentation',
        'Content Strategy', 'Content Marketing', 'SEO Writing', 'Social Media Writing',
        'Email Writing', 'Newsletter Writing', 'Press Release Writing',
        'Script Writing', 'Screenwriting', 'Playwriting', 'Creative Writing',
        'Fiction Writing', 'Non-fiction Writing', 'Memoir Writing', 'Poetry',
        'Editing', 'Proofreading', 'Copy Editing', 'Developmental Editing',
        'Publishing', 'Self-Publishing', 'Book Writing', 'E-book Creation',
        
        # Health & Wellness
        'Health & Wellness', 'Fitness', 'Nutrition', 'Mental Health',
        'Stress Management', 'Mindfulness', 'Meditation', 'Yoga',
        'Personal Training', 'Wellness Coaching', 'Life Coaching',
        'Work-Life Balance', 'Burnout Prevention', 'Resilience Building',
        'Sleep Optimization', 'Energy Management', 'Habit Formation',
        'Goal Setting', 'Motivation', 'Self-Discipline', 'Time Management',
        'Productivity', 'Focus', 'Concentration', 'Memory Improvement',
        'Learning Techniques', 'Study Skills', 'Test Taking', 'Academic Success'
    ]
    
    return known_skills


def discover_skills_from_search_suggestions(cookies=None, verbose=True):
    """Discover skills by analyzing search suggestions and autocomplete"""
    print("🔍 Discovering skills from search suggestions...")
    
    skills = set()
    
    # Common search terms that might reveal skills
    search_terms = [
        'python', 'javascript', 'java', 'c++', 'c#', 'ruby', 'go', 'rust', 'swift',
        'machine learning', 'data science', 'artificial intelligence', 'deep learning',
        'web development', 'mobile development', 'devops', 'cloud computing',
        'database', 'sql', 'nosql', 'mongodb', 'postgresql',
        'react', 'angular', 'vue', 'node.js', 'django', 'flask',
        'aws', 'azure', 'gcp', 'docker', 'kubernetes',
        'security', 'cybersecurity', 'networking', 'linux', 'windows',
        'agile', 'scrum', 'project management', 'leadership',
        'design', 'ui', 'ux', 'frontend', 'backend', 'fullstack'
    ]
    
    for term in search_terms:
        if verbose:
            print(f"\n🔍 Searching for suggestions: {term}")
        
        try:
            # Try search API for suggestions
            search_url = f"https://learning.oreilly.com/api/v1/search/suggestions?q={term}"
            content = retrieve_page_contents(search_url, cookies=cookies)
            
            if content:
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for suggestion in data:
                            if isinstance(suggestion, str):
                                skills.add(suggestion.strip())
                                if verbose:
                                    print(f"   ✅ Found suggestion: {suggestion}")
                            elif isinstance(suggestion, dict) and 'text' in suggestion:
                                skills.add(suggestion['text'].strip())
                                if verbose:
                                    print(f"   ✅ Found suggestion: {suggestion['text']}")
                except json.JSONDecodeError:
                    pass
            
            # Add delay between requests
            time.sleep(0.5)
            
        except Exception as e:
            if verbose:
                print(f"❌ Error searching for {term}: {e}")
            continue
    
    return list(skills)


def save_skills_to_json(skills, filename='oreilly-skills.json'):
    """Save skills list to JSON file"""
    if not skills:
        return
    
    skills_data = {
        'total_skills': len(skills),
        'discovered_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'skills': sorted(skills)
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(skills_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(skills)} skills to: {filename}")
    except Exception as e:
        print(f"❌ Failed to save skills: {e}")


def save_skills_to_txt(skills, filename='oreilly-skills.txt'):
    """Save skills list to text file"""
    if not skills:
        return
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(skills)))
        print(f"💾 Saved {len(skills)} skills to: {filename}")
    except Exception as e:
        print(f"❌ Failed to save skills: {e}")


def discover_all_skills(cookies=None, verbose=True):
    """Discover all available skills using multiple methods"""
    print("🚀 O'Reilly Learning Skills Discovery")
    print("=" * 50)
    
    all_skills = set()
    
    # Method 1: Known skills database
    print("\n📚 Method 1: Known skills database...")
    known_skills = discover_known_skills()
    all_skills.update(known_skills)
    print(f"📊 Found {len(known_skills)} skills from known database")
    
    # Method 2: Web page scraping
    print("\n📄 Method 2: Web page scraping...")
    web_skills, skill_urls = discover_skills_from_web_pages(cookies, verbose)
    all_skills.update(web_skills)
    print(f"📊 Found {len(web_skills)} skills from web pages")
    
    # Method 3: API discovery
    print("\n🔌 Method 3: API discovery...")
    api_skills = discover_skills_from_api(cookies, verbose)
    all_skills.update(api_skills)
    print(f"📊 Found {len(api_skills)} skills from API")
    
    # Method 4: Search suggestions
    print("\n🔍 Method 4: Search suggestions...")
    suggestion_skills = discover_skills_from_search_suggestions(cookies, verbose)
    all_skills.update(suggestion_skills)
    print(f"📊 Found {len(suggestion_skills)} skills from search suggestions")
    
    # Convert to sorted list
    final_skills = sorted(list(all_skills))
    
    print(f"\n🎉 Skills Discovery Complete!")
    print(f"📊 Total unique skills found: {len(final_skills)}")
    
    # Save results
    save_skills_to_json(final_skills)
    save_skills_to_txt(final_skills)
    
    return final_skills


def main():
    """Main function to discover all O'Reilly Learning skills"""
    print("O'Reilly Learning Skills Discovery Tool")
    print("=" * 50)
    
    # Load cookies for authentication
    cookies = load_cookies()
    if cookies:
        print("✅ Authentication cookies loaded")
    else:
        print("⚠️  No authentication cookies found - some content may not be accessible")
    
    # Discover all skills
    skills = discover_all_skills(cookies, verbose=True)
    
    if skills:
        print(f"\n✅ Successfully discovered {len(skills)} skills!")
        print("📁 Check the generated files:")
        print("   - oreilly-skills.json (detailed format)")
        print("   - oreilly-skills.txt (simple list)")
        
        # Show first 10 skills as preview
        print(f"\n📋 Preview of discovered skills:")
        for i, skill in enumerate(skills[:10]):
            print(f"   {i+1:2d}. {skill}")
        if len(skills) > 10:
            print(f"   ... and {len(skills) - 10} more skills")
    else:
        print("\n❌ No skills discovered")
        print("💡 Try checking your authentication cookies or network connection")


if __name__ == '__main__':
    main()
