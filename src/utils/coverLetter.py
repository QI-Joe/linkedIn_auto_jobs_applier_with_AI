# Windows-only: search/replace in Word, export PDF, then open PDF with default app
import os, platform
from pathlib import Path
import win32com.client as win32
import json

def open_with_default_app(path: Path):
    # from the Stack Overflow pattern: Windows uses os.startfile
    if platform.system() == "Windows":
        os.startfile(str(path))  # opens with default associated app

class CoverLetterPDF:

    def __init__(self):
        self.input_docx_folder = r"document_folder"
        self.job_type=r"A1-Cover Letter -- <replace>.docx"
        self.out_dir=os.path.join(self.input_docx_folder, "submitted")

    def word_replace_to_pdf_win(self, input_docx, replacements: dict, out_dir, target_name):
        input_docx = Path(input_docx).resolve()
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        output_pdf = out_dir / f"{target_name}.pdf"

        wdReplaceAll = 2 # means replace all occurrences, 1 means replace only first occurrence
        wdFormatPDF  = 17 # save as pdf format, 16 means save as docx format
        print(replacements)

        word = win32.gencache.EnsureDispatch("Word.Application")
        word.Visible = False  # set True if you want to watch Word
        try:
            doc = word.Documents.Open(str(input_docx))
            rng = doc.Content
            for old, new in replacements.items():
                find = rng.Find
                find.ClearFormatting()
                find.Replacement.ClearFormatting()
                find.Execute(FindText=old, ReplaceWith=new, Replace=wdReplaceAll)

            # Export directly to PDF at your specific path/name
            doc.SaveAs2(str(output_pdf), FileFormat=wdFormatPDF)
        finally:
            # Clean up
            doc.Close(False)
            word.Quit()

        # Preview result using default OS app (Windows uses os.startfile)
        # open_with_default_app(output_pdf)
        return output_pdf

    def load_history(self, selected_idx: int):
        recorded_last_job_name_path = r"./env/cover_letter_last_job.json"
        load_data = dict()
        with open(recorded_last_job_name_path, "r", encoding="utf-8") as f:
            load_data: dict = json.load(f)
        return load_data.get(selected_idx)

    def instant_save(self, data: dict):
        recorded_last_job_name_path = r"./env/cover_letter_last_job.json"
        with open(recorded_last_job_name_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # Example
    def load_and_generate(self, job_info: dict):
        company_name, job_title, file_suffix, selected_idx = job_info["company"], job_info["title"], job_info["selected_document"], job_info["selected_document_index"]
        resume, coverLetter = file_suffix
        loaded_history: dict = self.load_history(selected_idx)
        replacements = {
            k: v for k, v in zip(list(loaded_history.values()), [company_name, job_title])
        }
        
        input_docx = os.path.join(self.input_docx_folder, self.job_type.replace("<replace>", coverLetter))
        self.pdf = self.word_replace_to_pdf_win(
            input_docx=input_docx,
            replacements=replacements,
            out_dir=self.out_dir,
            target_name=f"Cover Letter {company_name}"
        )
        # Convert to absolute path for Selenium file upload
        self.resume_path = os.path.abspath(os.path.join(self.input_docx_folder, resume+".pdf"))
        
        print(f"resume path: {self.resume_path} \ncover letter path: {self.pdf}")
    
    def get_cover_letter_path(self):
        return self.pdf
    
    def get_resume_path(self):
        return self.resume_path