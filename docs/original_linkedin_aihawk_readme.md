# Original LinkedIn AIHawk Documentation

> **Note:** This is the original README from when this project was primarily focused on LinkedIn automation. The project has since expanded to support multiple job platforms.

<img src="../assets/linkedin_aihawk.png">

<!-- At first glance, the branding and messaging clearly conveys what to expect -->
<div align="center">

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/federico-elia-5199951b6/)
[![Gmail](https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:federico.elia.majo@gmail.com)

# LinkedIn_AIHawk

#### 🤖🔍 Your AI-powered job search assistant. Automate applications, get personalized recommendations, and land your dream job faster.

</div>
<br />

<!-- Message Clarity -->
## 🚀 Join the AIHawk Community 🚀 

Connect with like-minded individuals and get the most out of AIHawk.

💡 **Get support:** Ask questions, troubleshoot issues, and find solutions.

🗣️ **Share knowledge:** Share your experiences, tips, and best practices.

🤝 **Network:** Connect with other professionals and explore new opportunities.

🔔 **Stay updated:** Get the latest news and updates on AIHawk.

<!-- Strong Call to Action -->
### Join Now 👇
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white
)](https://t.me/AIhawkCommunity)




<!-- 🚀 **Join Our Telegram Community!** 🚀

Join our **Telegram community** for:
- **Support with AIHawk software**
- **Share your experiences** with AIhawk and learn from others
- **Job search tips** and **resume advice**
- **Idea exchange** and resources for your projects

📲 **[Join now!](https://t.me/AIhawkCommunity)** -->

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Documentation](#Documentation)
7. [Troubleshooting](#troubleshooting)
8. [Conclusion](#conclusion)
9. [Contributors](#contributors)
10. [License](#license)
11. [Disclaimer](#Disclaimer)

## Introduction

LinkedIn_AIHawk is a cutting-edge, automated tool designed to revolutionize the job search and application process on LinkedIn. In today's fiercely competitive job market, where opportunities can vanish in the blink of an eye, this program offers job seekers a significant advantage. By leveraging the power of automation and artificial intelligence, LinkedIn_AIHawk enables users to apply to a vast number of relevant positions efficiently and in a personalized manner, maximizing their chances of landing their dream job.

### The Challenge of Modern Job Hunting

In the digital age, the job search landscape has undergone a dramatic transformation. While online platforms like LinkedIn have opened up a world of opportunities, they have also intensified competition. Job seekers often find themselves spending countless hours scrolling through listings, tailoring applications, and repetitively filling out forms. This process can be not only time-consuming but also emotionally draining, leading to job search fatigue and missed opportunities.

### Enter LinkedIn_AIHawk: Your Personal Job Search Assistant

LinkedIn_AIHawk steps in as a game-changing solution to these challenges. It's not just a tool; it's your tireless, 24/7 job search partner. By automating the most time-consuming aspects of the job search process, it allows you to focus on what truly matters - preparing for interviews and developing your professional skills.

## Features

1. **Intelligent Job Search Automation**
   - Customizable search criteria
   - Continuous scanning for new openings
   - Smart filtering to exclude irrelevant listings

2. **Rapid and Efficient Application Submission**
   - One-click applications using LinkedIn's "Easy Apply" feature
   - Form auto-fill using your profile information
   - Automatic document attachment (resume, cover letter)

3. **AI-Powered Personalization**
   - Dynamic response generation for employer-specific questions
   - Tone and style matching to fit company culture
   - Keyword optimization for improved application relevance

4. **Volume Management with Quality**
   - Bulk application capability
   - Quality control measures
   - Detailed application tracking

5. **Intelligent Filtering and Blacklisting**
   - Company blacklist to avoid unwanted employers
   - Title filtering to focus on relevant positions

6. **Dynamic Resume Generation**
   - Automatically creates tailored resumes for each application
   - Customizes resume content based on job requirements

7. **Secure Data Handling**
   - Manages sensitive information securely using YAML files

## Installation

**Please watch this video to set up your LinkedIn_AIHawk: [How to set up LinkedIn_AIHawk](https://youtu.be/gdW9wogHEUM) - https://youtu.be/gdW9wogHEUM**
0. **Confirmed succesfull runs OSs & Python**: Python 3.10, 3.11.9(64b), 3.12.5(64b) . Windows 10, Ubuntu 22
1. **Download and Install Python:**

   Ensure you have Python installed on your system. You can download Python from the official website: [python.org](https://www.python.org/downloads/) (choose version 3.10 or higher)

   - [How to install Python on Windows](https://www.geeksforgeeks.org/how-to-install-python-on-windows/)
   - [How to install Python on Linux](https://www.geeksforgeeks.org/how-to-install-python-on-linux/)
   - [How to Download and Install Python on macOS](https://www.geeksforgeeks.org/how-to-download-and-install-python-latest-version-on-macos-mac-os-x/)

2. **Download and Install Google Chrome:**
   - Download and install the latest version of Google Chrome in its default location from the [official website](https://www.google.com/chrome).

3. **Clone the repository:**
   ```bash
   git clone https://github.com/feder-cr/linkedIn_auto_jobs_applier_with_AI.git
   cd linkedIn_auto_jobs_applier_with_AI
   ```

4. **Activate virtual environment:**
   ```bash
   python -m venv virtual
   source virtual/bin/activate  # On Windows: virtual\Scripts\activate
   ```
   For more detailed instructions on virtual environments, check out this guide: [Creating Virtual Environments](https://docs.python.org/3/tutorial/venv.html)

5. **Install the required packages:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### 1. secrets.yaml

This file contains sensitive information. Never share or commit this file to version control.

- `email: [Your LinkedIn email]`
  - Replace with your LinkedIn account email address
- `password: [Your LinkedIn password]`
  - Replace with your LinkedIn account password
- `openai_api_key: [Your OpenAI API key]`
  - Replace with your OpenAI API key for GPT integration
  - Generate your OpenAI API key here: [OpenAI API Keys](https://platform.openai.com/account/api-keys)
  - Note: You need to add credit to your OpenAI account to use the API. You can add credit by visiting the [OpenAI billing dashboard](https://platform.openai.com/account/billing).



### 2. config.yaml

This file defines your job search parameters and bot behavior. Each section contains options that you can customize:

- `remote: [true/false]`
  - Set to `true` to include remote jobs, `false` to exclude them

- `experienceLevel:`
  - Set desired experience levels to `true`, others to `false`

- `jobTypes:`
  - Set desired job types to `true`, others to `false`

- `date:`
  - Choose one time range for job postings by setting it to `true`, others to `false`


- `positions:`
  - List job titles you're interested in, one per line

- `locations:`
  - List locations you want to search in, one per line

- `distance: [number]`
  - Set the radius for your job search in miles
  - Example: `distance: 50`

- `companyBlacklist:`
  - List companies you want to exclude from your search, one per line

- `titleBlacklist:`
  - List keywords in job titles you want to avoid, one per line

### 3. plain_text_resume.yaml

This file contains your resume information in a structured format. Fill it out with your personal details, education, work experience, and skills. This information is used to auto-fill application forms and generate customized resumes.

Each section has specific fields to fill out:

- `personal_information:`
  - This section contains basic personal details to identify yourself and provide contact information.
  
  ```yaml
  personal_information:
    name: ""
    surname: ""
    dateOfBirth: ""
    country: ""
    city: ""
    address: ""
    phonePrefix: ""
    phone: ""
    email: ""
    github: ""
    linkedin: ""
  ```

- `education_details:`
  - This section outlines your academic background, including degrees earned and relevant coursework.
  
  ```yaml
  education_details:
    - degree: ""
      university: ""
      gpa: ""
      graduation_year: ""
      field_of_study: ""
      exam:
        exam_name1: ""
        exam_name2: ""
  ```

- `experience_details:`
  - This section details your work experience, including job roles, companies, and key responsibilities.
  
  ```yaml
  experience_details:
    - position: ""
      company: ""
      employment_period: ""
      location: ""
      industry: ""
      key_responsibilities:
        - responsibility_1: ""
        - responsibility_2: ""
        - responsibility_3: ""
      skills_acquired:
        - skill_1: ""
        - skill_2: ""
  ```

- `projects:`
  - Include notable projects you have worked on, including personal or professional projects.

- `achievements:`
  - Highlight notable accomplishments or awards you have received.
  
  ```yaml
  achievements:
    - name: ""
      description: ""
  ```

- `certifications:`
  - Include any professional certifications you have earned.
  
  ```yaml
  certifications:
    - name: ""
      description: ""
  ```

- `languages:`
  - Detail the languages you speak and your proficiency level in each.
  
  ```yaml
  languages:
    - language: ""
      proficiency: ""
  ```

- `interests:`

  ```yaml
  interests:
    - interest: ""
  ```

- `availability:`
  - State your current availability or notice period.
  
  ```yaml
  availability:
    notice_period: ""
  ```

- `salary_expectations:`
  - Provide your expected salary range.
  
  ```yaml
  salary_expectations:
    salary_range_usd: ""
  ```

- `self_identification:`
  - Provide information related to personal identity, including gender and pronouns.
  
  ```yaml
  self_identification:
    gender: ""
    pronouns: ""
    veteran: ""
    disability: ""
    ethnicity: ""
  ```

- `legal_authorization:`
  - Indicate your legal ability to work in various locations.

- `work_preferences:`
  - Specify your preferences for work arrangements and conditions.
  
  ```yaml
  work_preferences:
    remote_work: ""
    in_person_work: ""
    open_to_relocation: ""
    willing_to_complete_assessments: ""
    willing_to_undergo_drug_tests: ""
    willing_to_undergo_background_checks: ""
  ```

### PLUS. data_folder_example

The `data_folder_example` folder contains a working example of how the files necessary for the bot's operation should be structured and filled out. This folder serves as a practical reference to help you correctly set up your work environment for the LinkedIn job search bot.

#### Contents

Inside this folder, you'll find example versions of the key files:

- `secrets.yaml`
- `config.yaml`
- `plain_text_resume.yaml`

These files are already populated with fictitious but realistic data. They show you the correct format and type of information to enter in each file.

#### Usage

Using this folder as a guide can be particularly helpful for:

1. Understanding the correct structure of each configuration file
2. Seeing examples of valid data for each field
3. Having a reference point while filling out your personal files


## Usage
0. **LinkedIn language**
   To ensure the bot works, your LinkedIn language must be set to English.
   
2. **Data Folder:**
   Ensure that your data_folder contains the following files:
   - `secrets.yaml`
   - `config.yaml`
   - `plain_text_resume.yaml`

3. **Run the Bot:**

   LinkedIn_AIHawk offers flexibility in how it handles your pdf resume:

- **Dynamic Resume Generation:**
  If you don't use the `--resume` option, the bot will automatically generate a unique resume for each application. This feature uses the information from your `plain_text_resume.yaml` file and tailors it to each specific job application, potentially increasing your chances of success by customizing your resume for each position.
- **Using a Specific Resume:**
  If you want to use a specific resume for all applications, place your resume PDF in the `data_folder` and use the `--resume` option followed by the filename (including the .pdf extension).

   ```bash
   python main.py --data_folder path/to/your/data_folder
   ```

   OR

   ```bash
   python main.py --data_folder path/to/your/data_folder --resume your_resume.pdf
   ```

4. **Preferred run mode for improved error handling and recovery:**
   For improved error handling and recovery, run the bot in resume mode:

   ```bash
   python main.py --data_folder path/to/your/data_folder --resume
   ```

## ⚠️ Troubleshooting

### Common Issues

1. **Connection lost during application process:**
   Run the bot in `--resume` mode to continue from where it left off:
   ```bash
   python main.py --data_folder path/to/your/data_folder --resume
   ```

2. **Missing or incorrect configuration:**
   Verify all required files are present in your data folder:
   - `config.yaml`
   - `secrets.yaml`
   - `plain_text_resume.yaml`

3. **ChromeDriver issues:**
   The bot automatically downloads the correct ChromeDriver. If issues persist:
   - Ensure Google Chrome is installed in the default location
   - Check your internet connection
   - Try deleting and reinstalling Chrome

4. **Login failures:**
   - Verify your LinkedIn credentials in `secrets.yaml`
   - Check if you have 2FA enabled (currently not supported)
   - Ensure your account is in good standing

5. **Rate limiting:**
   - Reduce application frequency by adjusting delay in the script
   - Use VPN if necessary
   - Consider running the bot during off-peak hours

### Getting Help

If you encounter issues not listed above:

1. Check the console output for specific error messages
2. Ensure all dependencies are properly installed
3. Verify your configuration files are correctly formatted
4. Join our community for support: [Telegram](https://t.me/AIhawkCommunity)

## Documentation

For more detailed documentation, including advanced configuration options and troubleshooting, visit our [documentation site](docs/) or check out our [video tutorials](https://youtu.be/gdW9wogHEUM).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool automates job applications on LinkedIn. Please be aware that using this tool may violate LinkedIn's Terms of Service. Use it at your own risk and consider the potential consequences of automated job applications. The developers are not responsible for any consequences resulting from the use of this tool, including but not limited to account restrictions or suspensions.

Additionally, be mindful of the impact your automated applications might have on recruiters and the job application ecosystem. Use this tool responsibly and consider personalizing your applications even when using automation.

## Contributing

Contributions to this project are welcome! Please fork the repository and submit a pull request with your changes. Make sure to follow the existing code style and add tests for new features.

## Acknowledgements

- Thanks to the open-source community for the various libraries and tools used in this project.
- Special recognition to all contributors who help improve this tool.

---

*Happy job hunting! 🚀*