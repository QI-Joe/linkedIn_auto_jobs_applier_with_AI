from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml

@dataclass
class EducationDetail:
    education_level: str
    institution: str
    field_of_study: str
    final_evaluation_grade: str
    year_of_completion: int

@dataclass
class VisaInHK:
    visa_situation: str
    visa_type: str

@dataclass
class DevelopRole:
    ai_reseachers: str
    ai_engineer: str
    software_engineer: str
    backend_engineer: str
    frontend_engineer: str
    data_analyst: str

@dataclass
class ProgrammingLanguages:
    language: str

@dataclass
class ExperienceDetail:
    position: str
    company: str
    employment_period: str
    location: str
    industry: str
    key_responsibilities: List[str]
    skills_acquired: List[str]

@dataclass
class Language:
    language: str
    proficiency: str

@dataclass
class Availability:
    notice_period: str

@dataclass
class SalaryExpectations:
    salary_range_usd: str

@dataclass
class SelfIdentification:
    gender: str
    pronouns: str
    disability: str
    ethnicity: str

@dataclass
class WorkPreferences:
    remote_work: str
    in_person_work: str
    open_to_relocation: str
    willing_to_complete_assessments: str
    willing_to_undergo_drug_tests: str
    willing_to_undergo_background_checks: str

@dataclass
class SimplifiedJobApplicationProfile:
    education_details: List[EducationDetail]
    visa_in_hk: VisaInHK
    develop_role: DevelopRole
    programming_languages: ProgrammingLanguages
    experience_details: List[ExperienceDetail]
    languages: List[Language]
    interests: List[str]
    availability: Availability
    salary_expectations: SalaryExpectations
    self_identification: SelfIdentification
    work_preferences: WorkPreferences

    def __init__(self, yaml_str: str):
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            raise ValueError("Error parsing YAML file.") from e
        except Exception as e:
            raise RuntimeError("An unexpected error occurred while parsing the YAML file.") from e

        if not isinstance(data, dict):
            raise TypeError("YAML data must be a dictionary.")

        # Process education_details
        try:
            self.education_details = [EducationDetail(**edu) for edu in data['education_details']]
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in education_details data.") from e
        except TypeError as e:
            raise TypeError(f"Error in education_details data: {e}") from e

        # Process VisaInHK
        try:
            self.visa_in_hk = VisaInHK(**data['VisaInHK'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in VisaInHK data.") from e
        except TypeError as e:
            raise TypeError(f"Error in VisaInHK data: {e}") from e

        # Process DevelopRole
        try:
            self.develop_role = DevelopRole(**data['DevelopRole'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in DevelopRole data.") from e
        except TypeError as e:
            raise TypeError(f"Error in DevelopRole data: {e}") from e

        # Process ProgrammingLanguages
        try:
            self.programming_languages = ProgrammingLanguages(**data['ProgrammingLanguages'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in ProgrammingLanguages data.") from e
        except TypeError as e:
            raise TypeError(f"Error in ProgrammingLanguages data: {e}") from e

        # Process experience_details
        try:
            experience_list = []
            for exp in data['experience_details']:
                # Convert responsibility dictionaries to list of strings
                responsibilities = []
                for key, value in exp['key_responsibilities'][0].items():
                    responsibilities.append(value)
                
                experience_detail = ExperienceDetail(
                    position=exp['position'],
                    company=exp['company'],
                    employment_period=exp['employment_period'],
                    location=exp['location'],
                    industry=exp['industry'],
                    key_responsibilities=responsibilities,
                    skills_acquired=exp['skills_acquired']
                )
                experience_list.append(experience_detail)
            self.experience_details = experience_list
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in experience_details data.") from e
        except TypeError as e:
            raise TypeError(f"Error in experience_details data: {e}") from e

        # Process languages
        try:
            self.languages = [Language(**lang) for lang in data['languages']]
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in languages data.") from e
        except TypeError as e:
            raise TypeError(f"Error in languages data: {e}") from e

        # Process interests (simple list)
        try:
            self.interests = data['interests']
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in interests data.") from e

        # Process availability
        try:
            self.availability = Availability(**data['availability'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in availability data.") from e
        except TypeError as e:
            raise TypeError(f"Error in availability data: {e}") from e

        # Process salary_expectations
        try:
            self.salary_expectations = SalaryExpectations(**data['salary_expectations'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in salary_expectations data.") from e
        except TypeError as e:
            raise TypeError(f"Error in salary_expectations data: {e}") from e

        # Process self_identification
        try:
            self.self_identification = SelfIdentification(**data['self_identification'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in self_identification data.") from e
        except TypeError as e:
            raise TypeError(f"Error in self_identification data: {e}") from e

        # Process work_preferences
        try:
            self.work_preferences = WorkPreferences(**data['work_preferences'])
        except KeyError as e:
            raise KeyError(f"Required field {e} is missing in work_preferences data.") from e
        except TypeError as e:
            raise TypeError(f"Error in work_preferences data: {e}") from e

    def get_programming_languages_list(self) -> List[str]:
        """Parse the comma-separated programming languages string into a list"""
        return [lang.strip() for lang in self.programming_languages.language.split(',')]

    def get_experience_years(self, role: str) -> str:
        """Get experience years for a specific role"""
        role_map = {
            'ai_researcher': self.develop_role.ai_reseachers,
            'ai_engineer': self.develop_role.ai_engineer,
            'software_engineer': self.develop_role.software_engineer,
            'backend_engineer': self.develop_role.backend_engineer,
            'frontend_engineer': self.develop_role.frontend_engineer,
            'data_analyst': self.develop_role.data_analyst
        }
        return role_map.get(role, "0 years")

    def is_visa_required(self) -> bool:
        """Check if visa sponsorship is required"""
        return self.visa_in_hk.visa_type not in ["IANG", "Work Visa", "Dependent Visa"]


    def __str__(self):
        def format_dataclass(obj):
            return "\n".join(f"{field.name}: {getattr(obj, field.name)}" for field in obj.__dataclass_fields__.values())

        return (f"Education Details: {len(self.education_details)} entries\n\n"
                f"Visa Status:\n{format_dataclass(self.visa_in_hk)}\n\n"
                f"Development Roles Experience:\n{format_dataclass(self.develop_role)}\n\n"
                f"Programming Languages: {self.programming_languages.language}\n\n"
                f"Work Experience: {len(self.experience_details)} positions\n\n"
                f"Languages: {len(self.languages)} languages\n\n"
                f"Interests: {', '.join(self.interests)}\n\n"
                f"Availability: {self.availability.notice_period}\n\n"
                f"Salary Expectations: {self.salary_expectations.salary_range_usd}\n\n"
                f"Self Identification:\n{format_dataclass(self.self_identification)}\n\n"
                f"Work Preferences:\n{format_dataclass(self.work_preferences)}\n\n")

# Utility function to load profile from file
def load_profile_from_file(file_path: str) -> SimplifiedJobApplicationProfile:
    """Load job application profile from YAML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            yaml_content = file.read()
        return SimplifiedJobApplicationProfile(yaml_content)
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Error loading profile from file: {e}")

# Example usage
if __name__ == "__main__":
    # Example of how to use the simplified profile
    try:
        profile = load_profile_from_file("./env/backup.yaml")
        print(profile)
        print("\nProgramming Languages List:", profile.get_programming_languages_list())
        print("AI Engineer Experience:", profile.get_experience_years('ai_engineer'))
        print("Visa Required:", profile.is_visa_required())
    except Exception as e:
        print(f"Error: {e}")