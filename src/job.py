from dataclasses import dataclass, field
from typing import Optional, Dict, Any

@dataclass
class Job:
    title: str
    company: str
    location: str
    link: str
    apply_method: str
    platform: str = "linkedin"  # NEW: Platform identifier
    description: str = ""
    summarize_job_description: str = ""
    pdf_path: str = ""
    recruiter_link: str = ""
    salary: str = ""  # NEW: Salary information
    job_type: str = ""  # NEW: Full-time, Part-time, Contract, etc.
    experience_level: str = ""  # NEW: Entry, Mid, Senior level
    industry: str = ""  # NEW: Industry classification
    skills_required: str = ""  # NEW: Required skills
    application_id: str = ""  # NEW: Platform-specific application ID
    date_posted: str = ""  # NEW: Job posting date
    company_size: str = ""  # NEW: Company size information
    remote_option: str = ""  # NEW: Remote/Hybrid/On-site
    platform_specific_data: Dict[str, Any] = field(default_factory=dict)  # NEW: Platform-specific additional data

    def set_summarize_job_description(self, summarize_job_description):
        self.summarize_job_description = summarize_job_description

    def set_job_description(self, description):
        self.description = description

    def set_recruiter_link(self, recruiter_link):
        self.recruiter_link = recruiter_link

    def set_salary(self, salary):
        """Set salary information"""
        self.salary = salary

    def set_job_type(self, job_type):
        """Set job type (Full-time, Part-time, etc.)"""
        self.job_type = job_type

    def set_experience_level(self, experience_level):
        """Set experience level requirement"""
        self.experience_level = experience_level

    def set_industry(self, industry):
        """Set industry classification"""
        self.industry = industry

    def set_skills_required(self, skills_required):
        """Set required skills"""
        self.skills_required = skills_required

    def set_application_id(self, application_id):
        """Set platform-specific application ID"""
        self.application_id = application_id

    def set_date_posted(self, date_posted):
        """Set job posting date"""
        self.date_posted = date_posted

    def set_company_size(self, company_size):
        """Set company size information"""
        self.company_size = company_size

    def set_remote_option(self, remote_option):
        """Set remote work option"""
        self.remote_option = remote_option

    def set_platform_data(self, key: str, value: Any):
        """Set platform-specific data"""
        self.platform_specific_data[key] = value

    def get_platform_data(self, key: str, default: Any = None) -> Any:
        """Get platform-specific data"""
        return self.platform_specific_data.get(key, default)

    def is_linkedin_job(self) -> bool:
        """Check if this is a LinkedIn job"""
        return self.platform.lower() == "linkedin"

    def is_jobsdb_job(self) -> bool:
        """Check if this is a JobsDB job"""
        return self.platform.lower() == "jobsdb"

    def formatted_job_information(self):
        """
        Formats the job information as a markdown string.
        Enhanced to include platform and additional fields.
        """
        # Build additional information section
        additional_info = []
        if self.salary:
            additional_info.append(f"- Salary: {self.salary}")
        if self.job_type:
            additional_info.append(f"- Job Type: {self.job_type}")
        if self.experience_level:
            additional_info.append(f"- Experience Level: {self.experience_level}")
        if self.industry:
            additional_info.append(f"- Industry: {self.industry}")
        if self.remote_option:
            additional_info.append(f"- Work Arrangement: {self.remote_option}")
        if self.company_size:
            additional_info.append(f"- Company Size: {self.company_size}")
        if self.date_posted:
            additional_info.append(f"- Posted: {self.date_posted}")

        additional_section = "\n".join(additional_info) if additional_info else "- No additional information available"

        job_information = f"""
        # Job Description
        ## Job Information 
        - Platform: {self.platform.title()}
        - Position: {self.title}
        - At: {self.company}
        - Location: {self.location}
        - Apply Method: {self.apply_method}
        - Recruiter Profile: {self.recruiter_link or 'Not available'}
        
        ## Additional Details
        {additional_section}
        
        ## Required Skills
        {self.skills_required or 'No specific skills mentioned.'}
        
        ## Description
        {self.description or 'No description provided.'}
        """
        return job_information.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary representation"""
        return {
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'link': self.link,
            'apply_method': self.apply_method,
            'platform': self.platform,
            'description': self.description,
            'summarize_job_description': self.summarize_job_description,
            'pdf_path': self.pdf_path,
            'recruiter_link': self.recruiter_link,
            'salary': self.salary,
            'job_type': self.job_type,
            'experience_level': self.experience_level,
            'industry': self.industry,
            'skills_required': self.skills_required,
            'application_id': self.application_id,
            'date_posted': self.date_posted,
            'company_size': self.company_size,
            'remote_option': self.remote_option,
            'platform_specific_data': self.platform_specific_data
        }

    # @classmethod
    # def from_dict(cls, data: Dict[str, Any]) -> 'Job':
    #     """Create job from dictionary representation"""
    #     return cls(
    #         title=data.get('title', ''),
    #         company=data.get('company', ''),
    #         location=data.get('location', ''),
    #         link=data.get('link', ''),
    #         apply_method=data.get('apply_method', ''),
    #         platform=data.get('platform', 'linkedin'),
    #         description=data.get('description', ''),
    #         summarize_job_description=data.get('summarize_job_description', ''),
    #         pdf_path=data.get('pdf_path', ''),
    #         recruiter_link=data.get('recruiter_link', ''),
    #         salary=data.get('salary', ''),
    #         job_type=data.get('job_type', ''),
    #         experience_level=data.get('experience_level', ''),
    #         industry=data.get('industry', ''),
    #         skills_required=data.get('skills_required', ''),
    #         application_id=data.get('application_id', ''),
    #         date_posted=data.get('date_posted', ''),
    #         company_size=data.get('company_size', ''),
    #         remote_option=data.get('remote_option', ''),
    #         platform_specific_data=data.get('platform_specific_data', {})
    #     )
