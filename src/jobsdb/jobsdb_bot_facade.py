from typing import Optional, Dict, Any, List
from src.jobsdb.jobsdb_authenticator import JobsDBAuthenticator
from src.jobsdb.jobsdb_job_manager import JobsDBJobManager
from src.utils.job_application_profile import JobApplicationProfile
from src.utils.gpt import GPTAnswerer


class JobsDBBotState:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.credentials_set: bool = False
        self.api_key_set: bool = False
        self.job_application_profile_set: bool = False
        self.gpt_answerer_set: bool = False
        self.parameters_set: bool = False
        self.logged_in: bool = False

    def validate_state(self, required_keys: List[str]) -> None:
        for key in required_keys:
            if not getattr(self, key):
                raise ValueError(f"{key.replace('_', ' ').capitalize()} must be set before proceeding.")


class JobsDBBotFacade:
    """
    JobsDB bot facade providing the same interface as LinkedInBotFacade
    but orchestrating JobsDB-specific components.
    """
    
    def __init__(self, login_component: JobsDBAuthenticator, apply_component: JobsDBJobManager) -> None:
        self.login_component: JobsDBAuthenticator = login_component
        self.apply_component: JobsDBJobManager = apply_component
        self.state: JobsDBBotState = JobsDBBotState()
        self.job_application_profile: Optional[JobApplicationProfile] = None
        self.resume: Optional[str] = False
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.parameters: Optional[Dict[str, Any]] = None

    def set_job_application_profile_and_resume(self, job_application_profile: JobApplicationProfile, resume: str) -> None:
        self._validate_non_empty(job_application_profile, "Job application profile")
        self._validate_non_empty(resume, "Resume")
        self.job_application_profile = job_application_profile
        self.resume = False
        self.state.job_application_profile_set = True

    def set_secrets(self, email: str, password: str) -> None:
        self._validate_non_empty(email, "Email")
        self._validate_non_empty(password, "Password")
        self.email = email
        self.password = password
        self.state.credentials_set = True

    def set_gpt_answerer_and_resume_generator(self, gpt_answerer_component: GPTAnswerer, resume_generator_manager: Optional[Any] = None) -> None:
        self._ensure_job_profile_and_resume_set()
        gpt_answerer_component.set_job_application_profile(self.job_application_profile)
        if self.resume:  # Only set resume if it exists
            gpt_answerer_component.set_resume(self.resume)
        self.apply_component.set_gpt_answerer(gpt_answerer_component)
        if resume_generator_manager:  # Only set if not None
            self.apply_component.set_resume_generator_manager(resume_generator_manager)
        self.state.gpt_answerer_set = True

    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        self._validate_non_empty(parameters, "Parameters")
        self.parameters = parameters
        self.apply_component.set_parameters(parameters)
        self.state.parameters_set = True

    def start_login(self) -> None:
        self.state.validate_state(['credentials_set'])
        self.login_component.set_secrets(self.email, self.password)
        self.login_component.start()
        self.state.logged_in = True

    def start_apply(self) -> None:
        self.state.validate_state(['logged_in', 'job_application_profile_set', 'gpt_answerer_set', 'parameters_set'])
        self.apply_component.apply_jobs()

    def _validate_non_empty(self, value: Any, name: str) -> None:
        if not value:
            raise ValueError(f"{name} cannot be empty.")

    def _ensure_job_profile_and_resume_set(self) -> None:
        if not self.state.job_application_profile_set:
            raise ValueError("Job application profile and resume must be set before proceeding.")
