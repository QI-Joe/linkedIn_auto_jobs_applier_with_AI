from src.utils.gpt import LoggerChatModel
from langchain_core.messages.ai import AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompt_values import StringPromptValue
from langchain_core.prompts import ChatPromptTemplate
from langchain_xai import ChatXAI
import src.utils.strings as strings

class SimplifedGPT:
    def __init__(self, open_ai_key: str, model_name: str = "grok-3-mini", temperature: float = 0.4):
        self.llm = ChatXAI(
            model=model_name, 
            temperature=temperature, 
        )
        
        self.model = LoggerChatModel(self.llm)
    
    def set_job_application_profile(self, job_application_profile):
        self.job_application_profile = job_application_profile
    
    def _create_chain(self, template: str):
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm | StrOutputParser()
    
    def standard_simplified_profile_chain(self, question: str):
        chains = {
            "experience_details": self._create_chain(strings.experience_details_template),
            "availability": self._create_chain(strings.availability_template),
            "salary_expectations": self._create_chain(strings.salary_expectations_template),
            "languages": self._create_chain(strings.languages_template),
            "visa_in_hk": self._create_chain(strings.visa_in_hk_template),
            "develop_role": self._create_chain(strings.develop_role_template),
            "programming_languages": self._create_chain(strings.programming_language_template),
        }
        
        section_prompt = """
        You are assisting a bot designed to automatically apply for jobs. The bot receives various questions about job applications and needs to determine the most relevant section of the profile to provide an accurate response.

        For the following question: '{question}', determine which section is most relevant. 
        Respond with exactly one of the following options:
        - Experience Details
        - Availability
        - Salary Expectations
        - Languages
        - Visa In HK
        - Develop Role
        - Programming Languages

        Guidelines for each section:

        1. **Experience Details**: Job positions, companies, responsibilities, skills acquired
        2. **Availability**: Notice period, when you can start
        3. **Salary Expectations**: Expected salary range
        4. **Languages**: Spoken languages and proficiency levels
        5. **Visa In HK**: Hong Kong work authorization and visa status
        6. **Develop Role**: Years of experience in different development roles
        7. **Programming Languages**: Technical programming skills

        Provide only the exact name of the section from the list above with no additional text.
        """
        
        prompt = ChatPromptTemplate.from_template(section_prompt)
        chain = prompt | self.llm | StrOutputParser()
        output = chain.invoke({"question": question})
        section_name = output.lower().replace(" ", "_")
        
        resume_section = getattr(self.job_application_profile, section_name, None)
        if resume_section is None:
            raise ValueError(f"Section '{section_name}' not found in job_application_profile.")
        
        chain = chains.get(section_name)
        if chain is None:
            raise ValueError(f"Chain not defined for section '{section_name}'")
        ai_answer = chain.invoke({"resume_section": resume_section, "question": question})
        
        return ai_answer.split(",")

